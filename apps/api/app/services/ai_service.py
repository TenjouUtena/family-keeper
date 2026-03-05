import base64
import io
import json
import logging
import time
from uuid import UUID

import anthropic
from fastapi import HTTPException, status
from PIL import Image

from app.config import settings
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_API_IMAGE_SIZE = 4_800_000  # Stay under Claude's 5MB base64 limit
MAX_IMAGE_DIMENSION = 2048  # Max width/height — larger is unnecessary for list extraction


class AIService:
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def check_rate_limit(self, family_id: UUID) -> None:
        """10 requests per family per hour, sliding window via Redis sorted set."""
        redis = await get_redis()
        key = f"ratelimit:ai:{family_id}"
        now = time.time()
        window = 3600  # 1 hour

        pipe = redis.pipeline()
        pipe.zremrangebyscore(key, 0, now - window)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window)
        results = await pipe.execute()

        if results[2] > settings.AI_RATE_LIMIT_PER_HOUR:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="AI rate limit exceeded (10 requests per hour per family)",
            )

    @staticmethod
    def _compress_image(image_bytes: bytes, mime_type: str) -> tuple[bytes, str]:
        """Resize and compress image to fit under Claude's 5MB limit.

        Returns (compressed_bytes, output_mime_type). Always outputs JPEG for
        best compression on photos.
        """
        img = Image.open(io.BytesIO(image_bytes))

        # Convert HEIC/palette/RGBA to RGB for JPEG output
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Downscale if larger than MAX_IMAGE_DIMENSION
        w, h = img.size
        if max(w, h) > MAX_IMAGE_DIMENSION:
            ratio = MAX_IMAGE_DIMENSION / max(w, h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
            logger.info("Resized image from %dx%d to %dx%d", w, h, img.size[0], img.size[1])

        # Compress as JPEG with decreasing quality until under limit
        for quality in (85, 70, 50, 30):
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            data = buf.getvalue()
            if len(data) <= MAX_API_IMAGE_SIZE:
                logger.info("Compressed image to %d bytes (quality=%d)", len(data), quality)
                return data, "image/jpeg"

        # Last resort: aggressive resize
        img = img.resize((img.size[0] // 2, img.size[1] // 2), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=50, optimize=True)
        data = buf.getvalue()
        logger.info("Aggressively resized image to %d bytes", len(data))
        return data, "image/jpeg"

    async def image_to_list(
        self,
        image_bytes: bytes,
        mime_type: str,
        list_type: str | None = None,
    ) -> dict:
        """Send image to Claude Vision and extract list items as JSON."""
        # Compress if needed (Claude API limit is 5MB for base64 images)
        image_b64 = base64.b64encode(image_bytes).decode()
        if len(image_b64) > MAX_API_IMAGE_SIZE:
            image_bytes, mime_type = self._compress_image(image_bytes, mime_type)
            image_b64 = base64.b64encode(image_bytes).decode()

        hint = f"This is a {list_type} list. " if list_type else ""
        prompt = (
            f"Extract all items from this image of a list. {hint}"
            "Return a JSON array of objects, each with a 'content' field (the item text) "
            "and an optional 'notes' field for any extra detail. "
            "Return ONLY valid JSON, no other text. Example: "
            '[{"content": "Milk", "notes": "2%"}, {"content": "Eggs"}]'
        )

        message = await self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": image_b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )

        logger.info(
            "ai_image_to_list tokens: input=%d output=%d",
            message.usage.input_tokens,
            message.usage.output_tokens,
        )

        raw_text = message.content[0].text.strip()
        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        items = json.loads(raw_text)

        return {
            "items": items,
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
        }
