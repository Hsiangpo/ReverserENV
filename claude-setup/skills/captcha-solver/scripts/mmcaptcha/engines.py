"""Normalize supported visual-model APIs to ask(images, prompt) -> text."""

from __future__ import annotations

import base64
import os

_lao_1_he = "munian_laohe"


def _data_url(image_bytes: bytes, mime: str = "image/png") -> str:
    return f"data:{mime};base64,{base64.b64encode(image_bytes).decode()}"


def _required_key(explicit: str | None, variable: str) -> str:
    value = explicit or os.environ.get(variable)
    if not value:
        raise RuntimeError(f"missing API key: pass api_key or set {variable}")
    return value


class VisionEngine:
    name = "base"

    def ask(self, image_bytes_list, prompt: str, mime: str = "image/png", timeout: int = 40) -> str:
        raise NotImplementedError


class DoubaoEngine(VisionEngine):
    """Volcengine Ark Responses API adapter."""

    name = "doubao"
    base_url = "https://ark.cn-beijing.volces.com/api/v3"
    default_model = "doubao-seed-1-6-vision-250815"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        try:
            from volcenginesdkarkruntime import Ark
        except ImportError as error:
            raise RuntimeError(
                "Doubao engine dependency is missing; install the pinned mmcaptcha "
                "requirements into the project venv"
            ) from error

        self.api_key = _required_key(api_key, "ARK_API_KEY")
        self.model = model or self.default_model
        self._client = Ark(base_url=self.base_url, api_key=self.api_key)

    def ask(self, image_bytes_list, prompt: str, mime: str = "image/png", timeout: int = 40) -> str:
        if isinstance(image_bytes_list, (bytes, bytearray)):
            image_bytes_list = [image_bytes_list]
        content = [
            {"type": "input_image", "image_url": _data_url(image, mime)}
            for image in image_bytes_list
        ]
        content.append({"type": "input_text", "text": prompt})
        response = self._client.responses.create(
            model=self.model,
            input=[{"role": "user", "content": content}],
            timeout=timeout,
        )
        return _extract_ark_text(response)


def _extract_ark_text(response) -> str:
    direct = getattr(response, "output_text", None)
    if isinstance(direct, str) and direct:
        return direct
    try:
        parts = []
        for item in response.output:
            for content in getattr(item, "content", []) or []:
                value = getattr(content, "text", None)
                if isinstance(value, str) and value:
                    parts.append(value)
        if parts:
            return "\n".join(parts)
    except (AttributeError, TypeError):
        pass
    raise ValueError("visual model response contains no text output")


class GLMEngine(VisionEngine):
    """Zhipu z.ai chat-completions adapter."""

    name = "glm"
    endpoint = "https://api.z.ai/api/paas/v4/chat/completions"
    default_model = "glm-4.5v"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        try:
            import requests
        except ImportError as error:
            raise RuntimeError(
                "GLM engine dependency is missing; install the pinned mmcaptcha "
                "requirements into the project venv"
            ) from error

        self._requests = requests
        self.api_key = _required_key(api_key, "ZAI_API_KEY")
        self.model = model or self.default_model

    def ask(self, image_bytes_list, prompt: str, mime: str = "image/png", timeout: int = 40) -> str:
        if isinstance(image_bytes_list, (bytes, bytearray)):
            image_bytes_list = [image_bytes_list]
        content = [
            {"type": "image_url", "image_url": {"url": _data_url(image, mime)}}
            for image in image_bytes_list
        ]
        content.append({"type": "text", "text": prompt})
        response = self._requests.post(
            self.endpoint,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": content}],
                "temperature": 0.1,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


_ENGINES = {"doubao": DoubaoEngine, "glm": GLMEngine}


def get_engine(name: str, **kwargs) -> VisionEngine:
    try:
        engine = _ENGINES[name]
    except KeyError as error:
        raise ValueError(f"unknown engine {name!r}; choose from {sorted(_ENGINES)}") from error
    return engine(**kwargs)
