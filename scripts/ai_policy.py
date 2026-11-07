"""Shared exact package policy for the AI-free desktop rebuild."""
import json
from pathlib import Path
import re

CONFIG = json.loads((Path(__file__).resolve().parents[1] / 'config/ai-free-desktop.json').read_text())
REBUILT = {name: version for source in CONFIG['sources'].values()
           for name, version in source['binaries'].items()}
ADDITIONS = set(CONFIG['additional_packages'])
REMOVALS = CONFIG['removals']
AI_NAME = re.compile(r'^(?:ai-kylin-|kyai-|kytensor-|libkyai-|libkylin-(?:.*ai|.*nlp|.*speech|.*vision|.*embedding)|'
                     r'libkysdk-(?:.*ai|ocr|mcp|vector-engine)|kylin-(?:ai|bot|.*-model)|'
                     r'onnxruntime-backend$|llm-backend$|libonnx|libtesseract|tesseract-ocr|libopencv-dnn)')


def is_ai_package(name):
    return name in REMOVALS or bool(AI_NAME.search(name))


def dependency_names(value):
    value = re.sub(r'\([^)]*\)|\[[^]]*\]', '', value)
    return re.findall(r'(?<![\w.-])[a-z0-9][a-z0-9+.-]*', value)


if __name__ == '__main__':
    print('\n'.join(sorted(set(REBUILT) | ADDITIONS)))
