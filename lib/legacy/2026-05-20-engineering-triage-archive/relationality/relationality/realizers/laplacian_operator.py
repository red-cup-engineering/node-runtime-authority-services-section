from __future__ import annotations

from typing import Any, Dict

import numpy as np

from relationality.models import RealizerContext, RecognitionObject
from .utils import clone_payload


def realize_laplacian_operator(input_obj: RecognitionObject, context: RealizerContext) -> Dict[str, Any]:
    phase_space = clone_payload(input_obj).get("phase_space", {})
    adjacency = phase_space.get("adjacency")
    if adjacency and isinstance(adjacency, list):
        matrix = np.array(adjacency, dtype=float)
    else:
        reachable = phase_space.get("reachable", []) or [1.0]
        n = max(2, len(reachable) + 1)
        weights = [abs(float(x)) if isinstance(x, (int, float)) else 1.0 for x in reachable]
        matrix = np.zeros((n, n))
        for i in range(n - 1):
            w = weights[i] if i < len(weights) else 1.0
            matrix[i, i + 1] = w
            matrix[i + 1, i] = w
    # Compute Laplacian L = D - A
    degree = np.diag(matrix.sum(axis=1))
    laplacian = degree - matrix
    eigenvalues, eigenvectors = np.linalg.eigh(laplacian)
    # Simple spectral entropy over normalized eigenvalues magnitude.
    mags = np.abs(eigenvalues)
    norm = mags.sum() if mags.sum() else 1.0
    probs = mags / norm
    spectral_entropy = float(-(probs * np.log(probs + 1e-12)).sum())
    dominant_index = int(np.argmax(mags)) if len(mags) else 0
    mean_degree = float(matrix.sum(axis=1).mean()) if matrix.size else 0.0
    spectral_diag = {
        "eigenvalues": eigenvalues.tolist(),
        "adjacency_used": adjacency is not None,
        "spectral_entropy": spectral_entropy,
        "dominant_mode": dominant_index,
        "mean_degree": mean_degree,
    }
    if adjacency:
        spectral_diag["adjacency"] = adjacency
    context.diagnostics.setdefault("spectral_effects", {})["laplacian"] = spectral_diag
    return {
        "kind": "SpectralGeometry",
        "acts": ["Laplacian", "Spectrum"],
        "payload": {
            "spectral_geometry": {
                "eigenvalues": eigenvalues.tolist(),
                "eigenvectors": eigenvectors.tolist(),
                "spectral_entropy": spectral_entropy,
                "dominant_mode": dominant_index,
                "mean_degree": mean_degree,
            }
        },
        "metadata": {"source": input_obj.id},
    }
