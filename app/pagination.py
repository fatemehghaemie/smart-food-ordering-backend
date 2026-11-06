from typing import Annotated

from fastapi import Query

Skip = Annotated[int, Query(ge=0, description="Number of items to skip")]
Limit = Annotated[int, Query(ge=1, le=100, description="Max items to return")]