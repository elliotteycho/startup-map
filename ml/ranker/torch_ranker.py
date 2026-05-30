"""Optional stretch: a small PyTorch pairwise (RankNet-style) neural ranker.

    pip install torch
    python -m ranker.torch_ranker [--synthetic] [--k 5]

Where the sklearn models score each (session, company) pointwise, this learns
directly from *pairs*: within a session, a clicked company should score higher
than a non-clicked one. The loss is the RankNet logistic on score differences.
Same features, same grouped split, same NDCG@k/AUC report -- so you can compare
a learned-to-rank objective against the pointwise baselines apples to apples.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from .data import load_dataset
from .features import build_preprocessor, engineer
from .metrics import evaluate
from sklearn.model_selection import GroupShuffleSplit


def _build_pairs(groups, y):
    """Within each session, pair every positive with every negative."""
    pos_idx, neg_idx = [], []
    for g in np.unique(groups):
        m = groups == g
        idx = np.where(m)[0]
        p = idx[y[idx] == 1]
        n = idx[y[idx] == 0]
        if len(p) and len(n):
            P, N = np.meshgrid(p, n)
            pos_idx.append(P.ravel())
            neg_idx.append(N.ravel())
    if not pos_idx:
        return np.array([]), np.array([])
    return np.concatenate(pos_idx), np.concatenate(neg_idx)


def main():
    try:
        import torch
        import torch.nn as nn
    except Exception:
        raise SystemExit("PyTorch not installed. Run: pip install torch")

    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--epochs", type=int, default=40)
    args = ap.parse_args()

    companies, events, source = load_dataset(force_synthetic=args.synthetic)
    frame = engineer(companies, events)
    print(f"Data source: {source} | rows={len(frame)} | pos rate={frame['y'].mean():.3f}")

    feat_cols = [c for c in frame.columns if c not in ("session_id", "company_id", "y")]
    gss = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=0)
    tr, te = next(gss.split(frame, frame["y"], groups=frame["session_id"]))
    train, test = frame.iloc[tr], frame.iloc[te]

    def _dense(x):
        return np.asarray(x.todense(), dtype="float32") if hasattr(x, "todense") else np.asarray(x, dtype="float32")

    prep = build_preprocessor().fit(train[feat_cols])
    Xtr = _dense(prep.transform(train[feat_cols]))
    Xte = _dense(prep.transform(test[feat_cols]))

    g_tr = train["session_id"].to_numpy()
    y_tr = train["y"].to_numpy()
    pi, ni = _build_pairs(g_tr, y_tr)
    if len(pi) == 0:
        raise SystemExit("No intra-session pos/neg pairs to train on.")

    torch.manual_seed(0)
    net = nn.Sequential(nn.Linear(Xtr.shape[1], 64), nn.ReLU(),
                        nn.Linear(64, 16), nn.ReLU(), nn.Linear(16, 1))
    opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-5)
    bce = nn.BCEWithLogitsLoss()

    Xt = torch.tensor(Xtr)
    Pp, Nn = torch.tensor(pi), torch.tensor(ni)
    for epoch in range(args.epochs):
        net.train()
        perm = torch.randperm(len(Pp))
        for batch in perm.split(4096):
            opt.zero_grad()
            diff = net(Xt[Pp[batch]]) - net(Xt[Nn[batch]])  # want > 0
            loss = bce(diff.squeeze(1), torch.ones(len(batch)))
            loss.backward()
            opt.step()

    net.eval()
    with torch.no_grad():
        scores = net(torch.tensor(Xte)).squeeze(1).numpy()
    print("PyTorch RankNet:", evaluate(test, scores, k=args.k))


if __name__ == "__main__":
    main()
