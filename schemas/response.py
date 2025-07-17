from pydantic import BaseModel, ConfigDict
from typing import List
from datetime import datetime
from enum import Enum

class ResultEnum(Enum):
    SUCCESS = 1
    FAILURE = 2

class ReponseModel(BaseModel):
    pass


class ResultSchema(ReponseModel):
    result: ResultEnum = ResultEnum.SUCCESS
