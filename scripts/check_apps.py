"""Fail closed: permit only version-pinned, reviewed desktop applications."""
import json
import pathlib
import subprocess
import sys

# Exact AI component families approved for this ISO; no generic library removal.
AI_COMPONENTS = {
    'ai-kylin-deepseek-r1-cloud-model',
    'ai-kylin-deepseek-v3-cloud-model',
    'ai-kylin-qwen-plus-cloud-model',
    'kyai-data-management-service',
    'kylin-ai-abstract-models',
    'kylin-ai-document-qa-service',
    'kylin-ai-document-service',
    'kylin-ai-engine-plugins',
    'kylin-ai-knowledge-base-service',
    'kylin-ai-parser-extension',
    'kylin-ai-python-env',
    'kylin-ai-runtime',
    'kylin-ai-subsystem',
    'kylin-ai-subsystem-modelconfig',
    'kylin-ai-subsystem-plugin',
    'kylin-ai-vector-engine',
    'kylin-bot',
    'kylin-cn-clip-model',
    'kylin-gte-base-model',
    'kylin-paddle-ocr-model',
    'kylin-portrait-matting-model',
    'kylin-sam-model',
    'kylin-sam-model-onnx',
    'kylin-speech-asr-model',
    'kylin-speech-asr-model-onnx',
    'kylin-speech-tts-model',
    'kylin-speech-tts-model-onnx',
    'kylin-universal-matting-model',
    'kytensor-client',
    'kytensor-llm',
    'kytensor-python',
    'kytensor-server',
    'libkyai-assistant0',
    'libkyai-business-framework',
    'libkyai-config0',
    'libkylin-ai-document-qa-service',
    'libkylin-ai-document-service',
    'libkylin-baidu-ai-engine-plugin',
    'libkylin-baidu-nlp-engine',
    'libkylin-baidu-speech-engine',
    'libkylin-baidu-vision-engine',
    'libkylin-coreai-embedding',
    'libkylin-custom-ai-engine-plugin',
    'libkylin-custom-nlp-engine',
    'libkylin-deepseek-ai-engine-plugin',
    'libkylin-deepseek-nlp-engine',
    'libkylin-freetrial-ai-engine-plugin',
    'libkylin-freetrial-nlp-engine',
    'libkylin-ondevice-ai-engine-plugin',
    'libkylin-ondevice-embedding-engine',
    'libkylin-ondevice-nlp-engine',
    'libkylin-ondevice-speech-engine',
    'libkylin-ondevice-traditional-ai-engine-plugin',
    'libkylin-ondevice-vision-engine',
    'libkylin-qwen-ai-engine-plugin',
    'libkylin-qwen-nlp-engine',
    'libkylin-xunfei-ai-engine-plugin',
    'libkylin-xunfei-nlp-engine',
    'libkylin-xunfei-speech-engine',
    'libkylin-xunfei-vision-engine',
    'libkysdk-genai-nlp0',
    'libkysdk-genai-vision0',
    'libkysdk-mcp',
    'libkysdk-vector-engine-client',
    'llm-backend',
    'onnxruntime-backend',
}
AI_INTEGRATION_FILES = {
    '/usr/lib/systemd/user/kylin-ai-vector-engine.service',
    '/usr/lib/systemd/user/kylin-ai-document-service.service',
    '/usr/lib/systemd/user/kylin-ai-knowledgebase-service.service',
    '/usr/lib/systemd/user/kylin-ai-document-qa-service.service',
    '/usr/share/polkit-1/actions/org.kylin-ai-subsystem-modelconfig.policy',
}


def read_status(text):
    packages = {}
    for paragraph in text.split('\n\n'):
        fields = {}
        for line in paragraph.splitlines():
            if line and not line[0].isspace() and ': ' in line:
                key, value = line.split(': ', 1)
                fields[key] = value
        if fields.get('Status') == 'install ok installed':
            packages[fields['Package']] = fields
    return packages


def check_app(name, fields, review, owned_files):
    if not isinstance(review, dict):
        raise ValueError(f'{name}: missing reviewed-apps.json entry')
    component = review.get('kind') == 'ai-component' and name in AI_COMPONENTS
    if name.startswith('lib') and not component:
        raise ValueError(f'{name}: shared libraries cannot be removed as desktop apps')
    for key in (('version', 'reason') if component else ('version', 'reason', 'desktop')):
        if not isinstance(review.get(key), str) or not review[key].strip():
            raise ValueError(f'{name}: missing review field {key}')
    if review['version'] != fields.get('Version'):
        raise ValueError(f'{name}: reviewed version differs from installed version')
    if fields.get('Essential') == 'yes' or fields.get('Protected') == 'yes':
        raise ValueError(f'{name}: Essential/Protected package')
    if fields.get('Priority', '').lower() not in ('optional', 'extra'):
        raise ValueError(f'{name}: only optional/extra applications may be removed')
    section = fields.get('Section', '').split('/')[-1]
    if component and review.get('section') != fields.get('Section'):
        raise ValueError(f'{name}: component section differs from reviewed metadata')
    if not component and section in {'admin', 'libs', 'libdevel', 'kernel', 'metapackages',
                   'x11', 'fonts', 'localization', 'debian-installer'}:
        raise ValueError(f'{name}: protected package section {section}')
    if not component:
        desktop = pathlib.PurePosixPath(review['desktop'])
        if (desktop.parent != pathlib.PurePosixPath('/usr/share/applications')
                or desktop.suffix != '.desktop' or str(desktop) not in owned_files):
            raise ValueError(f'{name}: must own the reviewed desktop launcher')
    # A desktop launcher alone is insufficient: system settings also own them.
    protected_prefixes = ('/boot/', '/lib/modules/', '/usr/lib/modules/',
                          '/lib/systemd/', '/usr/lib/systemd/',
                          '/usr/share/initramfs-tools/', '/etc/pam.d/',
                          '/usr/share/polkit-1/', '/usr/share/xsessions/',
                          '/usr/share/wayland-sessions/')
    if any(path.startswith(protected_prefixes) and not (component and path in AI_INTEGRATION_FILES)
           for path in owned_files):
        raise ValueError(f'{name}: owns protected system integration files')


def main():
    root, list_file, review_file = map(pathlib.Path, sys.argv[1:])
    installed = read_status((root / 'var/lib/dpkg/status').read_text())
    reviews = json.loads(review_file.read_text())
    selected = [line.split('#', 1)[0].strip() for line in list_file.read_text().splitlines()]
    for name in filter(None, selected):
        if name not in installed:
            raise ValueError(f'{name}: not installed')
        files = subprocess.check_output(['chroot', str(root), 'dpkg-query', '-L', name], text=True).splitlines()
        file_paths = [p for p in files if not (root / p.lstrip('/')).is_dir()]
        check_app(name, installed[name], reviews.get(name), file_paths)
        if reviews[name].get('kind') != 'ai-component':
            launcher = root / reviews[name]['desktop'].lstrip('/')
            if not launcher.is_file():
                raise ValueError(f'{name}: launcher missing')
        print(f'APPROVED\t{name}\t{reviews[name]["version"]}\t{reviews[name]["reason"]}')


if __name__ == '__main__':
    main()
