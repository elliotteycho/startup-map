"""TensorFlow / Keras click-through ranker.

    pip install tensorflow            # needs Python <= 3.12 today
    python -m ranker.tf_ranker [--synthetic] [--k 5] [--epochs 15]

A Keras MLP trained as a pointwise CTR model on the same engineered features,
the same session-grouped split, and the same NDCG@k / AUC / precision@k report
as the sklearn and PyTorch models -- so TensorFlow sits in the same benchmark
table as the others rather than as a bolt-on.
"""
from __future__ import annotations

import argparse

import numpy as np
from sklearn.model_selection import GroupShuffleSplit

from .data import load_dataset
from .features import build_preprocessor, engineer
from .metrics import evaluate


def _to_dense(x):
    return np.asarray(x.todense(), dtype="float32") if hasattr(x, "todense") else np.asarray(x, dtype="float32")


def main():
    try:
        import tensorflow as tf
        from tensorflow import keras
    except Exception:
        raise SystemExit("TensorFlow not installed. Run: pip install tensorflow (Python <= 3.12).")

    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--epochs", type=int, default=15)
    args = ap.parse_args()

    companies, events, source = load_dataset(force_synthetic=args.synthetic)
    frame = engineer(companies, events)
    print(f"Data source: {source} | rows={len(frame)} | pos rate={frame['y'].mean():.3f}")

    feat_cols = [c for c in frame.columns if c not in ("session_id", "company_id", "y")]
    gss = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=0)
    tr, te = next(gss.split(frame, frame["y"], groups=frame["session_id"]))
    train, test = frame.iloc[tr], frame.iloc[te]

    prep = build_preprocessor().fit(train[feat_cols])
    Xtr, Xte = _to_dense(prep.transform(train[feat_cols])), _to_dense(prep.transform(test[feat_cols]))
    ytr = train["y"].to_numpy().astype("float32")

    tf.random.set_seed(0)
    model = keras.Sequential([
        keras.layers.Input(shape=(Xtr.shape[1],)),
        keras.layers.Dense(64, activation="relu"),
        keras.layers.Dropout(0.2),
        keras.layers.Dense(16, activation="relu"),
        keras.layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer=keras.optimizers.Adam(1e-3),
                  loss="binary_crossentropy",
                  metrics=[keras.metrics.AUC(name="auc")])
    model.fit(Xtr, ytr, epochs=args.epochs, batch_size=256, verbose=0,
              class_weight={0: 1.0, 1: float((ytr == 0).sum() / max((ytr == 1).sum(), 1))})

    scores = model.predict(Xte, verbose=0).ravel()
    print("TensorFlow/Keras CTR:", evaluate(test, scores, k=args.k))


if __name__ == "__main__":
    main()
