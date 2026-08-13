"""Seed parent and Demucs subprocess RNGs for repeatable benchmark evidence."""
import os
import random

SEED = int(os.environ.get("AUTOMIX_DETERMINISTIC_SEED", "0"))
random.seed(SEED)

try:
    import numpy as np
    np.random.seed(SEED)
except ImportError:
    pass

try:
    import torch
    torch.manual_seed(SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(SEED)
except ImportError:
    pass
