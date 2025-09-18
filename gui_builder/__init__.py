try:
    from enum import StrEnum
except ImportError:
    from backports.strenum import StrEnum


class DialogResult(StrEnum):
    OK = "ok"
    APPLY = "apply"
    CANCEL = "cancel"
    YES = "yes"
    NO = "no"
    CLOSE = "close"
    FIND = "find"
    VETO = "veto"


# Maintain backward compatibility
OK = DialogResult.OK
APPLY = DialogResult.APPLY
CANCEL = DialogResult.CANCEL
YES = DialogResult.YES
NO = DialogResult.NO
CLOSE = DialogResult.CLOSE
FIND = DialogResult.FIND
VETO = DialogResult.VETO
