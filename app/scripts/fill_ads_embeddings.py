from __future__ import annotations

import asyncio
import logging
from typing import Iterable

import typer
from sqlalchemy import select

from app.core.settings import get_settings
from app.db.models import Ad
from app.db.session import get_sessionmaker
from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


def _build_embedding_text(ad: Ad) -> str:
    keywords = ad.keywords or []
    keywords_text = ", ".join(keywords) if keywords else ""

    parts: list[str] = [f"Ad Title: {ad.title}", f"Ad Description: {ad.description}"]
    if keywords_text:
        parts.append(f"Ad Keywords: {keywords_text}")

    parts.insert(0, "Type: Advertisement/Commercial Offer")

    return "\n".join(parts)


def _chunked(items: list[Ad], size: int) -> Iterable[list[Ad]]:
    if size <= 0:
        raise ValueError("batch size must be positive")
    for i in range(0, len(items), size):
        yield items[i: i + size]


async def run_backfill(
    *, fetch_size: int = 200, embed_batch_size: int = 32, force: bool = False
) -> int:
    settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    service = GeminiService(settings=settings)
    SessionLocal = get_sessionmaker(settings.database_url)

    total_updated = 0
    total_skipped = 0

    mode = "ALL ads (force mode)" if force else "only NULL embeddings"
    logger.info(
        "Starting embeddings backfill (%s). model=%s dim=%s",
        mode,
        settings.gemini_embedding_model,
        settings.gemini_embedding_dim,
    )

    with SessionLocal() as session:
        while True:
            query = select(Ad).order_by(Ad.id.asc()).limit(fetch_size)
            if not force:
                query = query.where(Ad.embedding.is_(None))
            
            ads: list[Ad] = (
                session.execute(query)
                .scalars()
                .all()
            )

            if not ads:
                break

            status = "for processing" if force else "with NULL embedding"
            logger.info("Fetched %d ads %s", len(ads), status)

            for batch in _chunked(ads, embed_batch_size):
                texts = [_build_embedding_text(ad) for ad in batch]
                vectors = await service.embed_texts(texts)

                updated = 0
                skipped = 0

                for ad, vec in zip(batch, vectors, strict=True):
                    # Defensive: if another process filled it between fetch and update.
                    if not force and ad.embedding is not None:
                        skipped += 1
                        continue
                    ad.embedding = vec
                    updated += 1

                session.commit()

                total_updated += updated
                total_skipped += skipped

                logger.info(
                    "Committed batch: updated=%d skipped=%d total_updated=%d",
                    updated,
                    skipped,
                    total_updated,
                )

    logger.info(
        "Backfill completed. total_updated=%d total_skipped=%d",
        total_updated,
        total_skipped,
    )
    return total_updated


app = typer.Typer()


@app.command()
def main(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Update embeddings for all ads, even if they already have embeddings",
    ),
) -> None:
    """Backfill embeddings for ads in the database."""
    asyncio.run(run_backfill(force=force))


if __name__ == "__main__":
    app()
