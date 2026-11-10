from dataclasses import dataclass, field


@dataclass(frozen=True)
class HttpRequest:
    method: str
    path: str
    body: dict = field(default_factory=dict)  # parsed JSON body


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: dict
