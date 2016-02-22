ACCOUNT_ID = ''
LAMBDA = {
    'Prefix': ''
}
ENDPOINTS = [

]


def load_project_settings(settings_module):
    for name in dir(settings_module):
        if name.startswith('__'):
            continue
        globals()[name] = getattr(settings_module, name)
