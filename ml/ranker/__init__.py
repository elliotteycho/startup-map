"""Startup Map internship ranker.

A learning-to-rank / click-through model that orders companies for a given
student session by predicted relevance. Trains on the `events` click stream
joined to `companies` features; evaluates with grouped AUC, NDCG@k, and
precision@k. Mirrors the production ad-ranking problem: features + objective
+ ranking metric.
"""
