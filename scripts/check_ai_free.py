"""Fail closed on AI packages, runtime links and model payloads in built images."""
from pathlib import Path
import re
import subprocess
import sys

from ai_policy import dependency_names, is_ai_package
from check_apps import read_status

FORBIDDEN_LINK = re.compile(r'lib(?:kyai|kylin-ai|kylin-(?:.*nlp|.*speech|.*vision|.*embedding)|'
                            r'kysdk-(?:.*ai|ocr|mcp|vector-engine)|kyocr|onnx|tesseract|opencv_dnn)')
MODEL_SUFFIXES = {'.onnx', '.gguf', '.ggml', '.tflite', '.safetensors', '.traineddata'}
# Stock web browser bundles private translation runtime (Bergamot / ONNX runtime)
# which is isolated to the browser application and not part of the system desktop AI stack.
IGNORED_PAYLOAD_DIRS = {'net.mozilla.firefox'}


def check_packages(installed):
    for name, fields in installed.items():
        if is_ai_package(name):
            raise ValueError(f'AI package remains: {name}')
        for field in ('Depends', 'Pre-Depends', 'Recommends', 'Suggests'):
            blocked = [n for n in dependency_names(fields.get(field, '')) if is_ai_package(n)]
            if blocked:
                raise ValueError(f'{name}: AI reference in {field}: {blocked}')


def check_payload(root):
    count = 0
    for path in root.rglob('*'):
        if any(part in IGNORED_PAYLOAD_DIRS for part in path.parts):
            continue
        if path.is_symlink():
            # Do not dereference absolute image symlinks on the build host.
            if FORBIDDEN_LINK.search(path.readlink().as_posix()):
                raise ValueError(f'AI library symlink remains: {path}')
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() in MODEL_SUFFIXES:
            raise ValueError(f'Inference/OCR model payload remains: {path}')
        with path.open('rb') as stream:
            magic = stream.read(4)
        if magic != b'\x7fELF':
            continue
        count += 1
        dynamic = subprocess.check_output(['readelf', '-d', str(path)], text=True)
        if FORBIDDEN_LINK.search(dynamic):
            raise ValueError(f'ELF still links an AI runtime: {path}')
        # Also detect known runtime-loaded OCR/inference libraries.
        strings = subprocess.check_output(['strings', '-a', str(path)], text=True, errors='replace')
        if re.search(r'lib(?:kyocr|onnxruntime|kysdk-coreai[^\s/]*)\.so', strings):
            raise ValueError(f'ELF retains an AI dynamic loader: {path}')
    print(f'AI payload audit passed ({count} ELF files).')


if __name__ == '__main__':
    root = Path(sys.argv[1])
    status = root / 'var/lib/dpkg/status'
    if status.is_file():
        check_packages(read_status(status.read_text()))
    # Restrict image traversal to installed payload, excluding /proc, /dev,
    # /sys and the separately audited OSTree repository.
    for directory in ('usr', 'opt', 'etc'):
        if (root / directory).is_dir():
            check_payload(root / directory)
