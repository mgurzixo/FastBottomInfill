# Copyright (c) 2022 5@xes
# The CuraSlowZ is released under the terms of the AGPLv3 or higher.

from . import FastBottomInfill


def getMetaData():
    return {}

def register(app):
    return {"extension": FastBottomInfill.FastBottomInfill()}
