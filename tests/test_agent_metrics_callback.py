from app.services.agent_metrics_callback import MetricsCallbackHandler


def test_metrics_callback_tracks_embedding_tokens_separately():
    cb = MetricsCallbackHandler()
    cb.total_tokens = 120

    cb.add_embedding_tokens(30)
    cb.add_embedding_tokens(0)
    cb.add_embedding_tokens(-5)

    metrics = cb.get_metrics()
    assert metrics["llm_tokens"] == 120
    assert metrics["embedding_tokens"] == 30
    assert metrics["total_tokens"] == 120
    assert metrics["total_with_embeddings"] == 150

    cb.reset()
    reset_metrics = cb.get_metrics()
    assert reset_metrics["llm_tokens"] == 0
    assert reset_metrics["embedding_tokens"] == 0
    assert reset_metrics["total_tokens"] == 0
    assert reset_metrics["total_with_embeddings"] == 0
