from __future__ import annotations

import sys

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from tokenization_premium import __version__


def test_python_and_package_contract() -> None:
    assert sys.version_info[:2] == (3, 12)
    assert __version__


def test_tabular_and_tokenization_smoke() -> None:
    frame = pd.DataFrame({"text": ["token premium", "premium research"]})
    matrix = TfidfVectorizer().fit_transform(frame["text"])
    assert frame.shape == (2, 1)
    assert isinstance(matrix.toarray(), np.ndarray)
    assert matrix.shape == (2, 3)

