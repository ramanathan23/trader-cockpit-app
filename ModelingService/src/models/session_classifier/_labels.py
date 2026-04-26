from ._features import SESSION_CLASSES

CLASS_TO_ID = {label: idx for idx, label in enumerate(SESSION_CLASSES)}
ID_TO_CLASS = {idx: label for idx, label in enumerate(SESSION_CLASSES)}
