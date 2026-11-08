"""Fail closed on AI packages, runtime links and model payloads in built images."""
from pathlib import Path
import os
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
FIREFOX_PAYLOAD = ('opt/apps/net.mozilla.firefox', 'var/opt/apps/net.mozilla.firefox')


def check_packages(installed):
    for name, fields in installed.items():
        if is_ai_package(name):
            raise ValueError(f'AI package remains: {name}')
        for field in ('Depends', 'Pre-Depends', 'Recommends', 'Suggests'):
            blocked = [n for n in dependency_names(fields.get(field, '')) if is_ai_package(n)]
            if blocked:
                raise ValueError(f'{name}: AI reference in {field}: {blocked}')


def dynamic_headers(path):
    # readelf processes PT_INTERP even for --dynamic. Detached debug ELFs can
    # retain program headers without interpreter bytes (binutils Debian #1012107).
    # Keep readelf for architecture-independent inspection; only that exact
    # diagnostic can fall back to objdump. Every other failure stays fatal.
    environment = dict(os.environ, LC_ALL='C')
    result = subprocess.run(['readelf', '-d', str(path)], capture_output=True,
                            text=True, errors='replace', env=environment)
    if result.returncode == 0 and not result.stderr.strip():
        return result.stdout
    known = 'readelf: Error: Unable to find program interpreter name'
    diagnostics = [line.strip() for line in result.stderr.splitlines() if line.strip()]
    if diagnostics and all(line == known for line in diagnostics):
        fallback = subprocess.run(['objdump', '-p', str(path)], capture_output=True,
                                  text=True, errors='replace', env=environment)
        if fallback.returncode == 0 and not fallback.stderr.strip():
            print(f'PT_INTERP metadata unavailable; dependencies audited with objdump: {path}')
            return fallback.stdout
        raise ValueError(f'Cannot audit ELF {path}: objdump exit {fallback.returncode}: '
                         f'{fallback.stderr.strip()}')
    raise ValueError(f'Cannot audit ELF {path}: readelf exit {result.returncode}: '
                     f'{result.stderr.strip()}')


def check_payload(root, excluded=()):
    count = 0
    for path in root.rglob('*'):
        if any(path == directory or directory in path.parents for directory in excluded):
            continue
        if path.is_symlink():
            # Do not dereference absolute image symlinks on the build host.
            if FORBIDDEN_LINK.search(path.readlink().as_posix()):
                raise ValueError(f'AI library symlink remains: {path}')
            continue
        if not path.is_file():
            continue
        if FORBIDDEN_LINK.search(path.name) or re.search(r'libonnxruntime.*\.so', path.name):
            raise ValueError(f'AI runtime payload remains: {path}')
        if path.suffix.lower() in MODEL_SUFFIXES:
            raise ValueError(f'Inference/OCR model payload remains: {path}')
        with path.open('rb') as stream:
            magic = stream.read(4)
        if magic != b'\x7fELF':
            continue
        count += 1
        dynamic = dynamic_headers(path)
        if FORBIDDEN_LINK.search(dynamic):
            raise ValueError(f'ELF still links an AI runtime: {path}')
        # Also detect known runtime-loaded OCR/inference libraries.
        strings = subprocess.check_output(['strings', '-a', str(path)], text=True, errors='replace')
        if re.search(r'lib(?:kyocr|onnxruntime|kysdk-coreai[^\s/]*)\.so', strings):
            raise ValueError(f'ELF retains an AI dynamic loader: {path}')
    print(f'AI payload audit passed ({count} ELF files).')


def check_image(root):
    status = root / 'var/lib/dpkg/status'
    if status.is_file():
        check_packages(read_status(status.read_text()))
    # Restrict image traversal to installed payload, excluding /proc, /dev,
    # /sys and the separately audited OSTree repository.
    excluded = tuple(root / path for path in FIREFOX_PAYLOAD)
    print('Scope: system AI; Firefox private payload explicitly retained.')
    for directory in ('usr', 'opt', 'etc', 'var/opt', 'var/lib'):
        if (root / directory).is_dir():
            check_payload(root / directory, excluded)


if __name__ == '__main__':
    check_image(Path(sys.argv[1]))
