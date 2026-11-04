"""User-reviewed probe for pytorch/extension-cpp; never called by the Web service."""
from __future__ import annotations

import argparse
import importlib
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-device', required=True, help='Expected substring in GPU device name')
    parser.add_argument('--module', default='extension_cpp')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repeats', type=int, default=100)
    args = parser.parse_args()
    if not args.expected_device.strip() or not 10 <= args.repeats <= 10000:
        parser.error('Provide a nonblank device name and 10–10000 repeats')
    result = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'build': 'not-evaluated',
              'functional': 'not-run', 'performance': 'not-run'}
    code = 1
    try:
        import torch
        device = torch.cuda.get_device_name(0)
        if args.expected_device.casefold() not in device.casefold():
            raise RuntimeError('Actual device does not match --expected-device')
        result['environment'] = {'device': device, 'torch': torch.__version__}
        extension = importlib.import_module(args.module)
        torch.manual_seed(0)
        for size in (1, 33, 1024, 1048576):
            a, b = torch.randn(size, device='cuda'), torch.randn(size, device='cuda')
            torch.testing.assert_close(extension.ops.mymuladd(a, b, 1.0), a * b + 1.0,
                                       rtol=1e-4, atol=1e-5)
        result['functional'] = 'passed'
        for _ in range(20):
            extension.ops.mymuladd(a, b, 1.0)
        samples = []
        for _ in range(args.repeats):
            torch.cuda.synchronize()
            start = time.perf_counter()
            extension.ops.mymuladd(a, b, 1.0)
            torch.cuda.synchronize()
            samples.append((time.perf_counter() - start) * 1000)
        result['performance'] = 'measured'  # Measurement is not a performance acceptance decision.
        result['timing'] = {'median_ms': statistics.median(samples), 'min_ms': min(samples),
                            'max_ms': max(samples), 'repeats': args.repeats, 'warmup': 20,
                            'elements': 1048576, 'dtype': 'float32'}
        code = 0
    except Exception as error:
        result['error'] = str(error)
        if result['functional'] == 'not-run':
            result['functional'] = 'failed'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
