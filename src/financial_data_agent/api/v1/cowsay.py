from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["Cowsay"])


@router.get("/cow", response_class=PlainTextResponse)
def get_cow() -> str:
    """Cowsay."""
    return r"""
  _____________
< hello world >
 -------------
        \   ^__^
         \  (oo)\_______
            (__)\       )\/\
                ||----w |
                ||     ||
"""
