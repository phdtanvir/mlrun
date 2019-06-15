from os import path
import click
import json
import os
from ast import literal_eval
import getpass
from tempfile import mktemp

from .runtimes import remote_run
from .secrets import SecretsStore

@click.group()
def main():
    pass

@main.command()
@click.argument("file", type=str)
@click.option('--param', '-p', default='', multiple=True,
              help="parameter name and value tuples, e.g. -p x=37 -p y='text'")
@click.option('--in-artifact', '-i', multiple=True, help='input artifact')
@click.option('--out-artifact', '-o', multiple=True, help='output artifact')
@click.option('--in-path', help='default input path/url (prefix) for artifact')
@click.option('--out-path', help='default output path/url (prefix) for artifact')
@click.option('--secrets', '-s', multiple=True, help='secrets file=<filename> or env=ENV_KEY1,..')
@click.option('--uid', help='unique run ID')
@click.option('--name', help='run name')
@click.option('--workflow', help='workflow name/id')
@click.option('--save-to', default='', help='save run results yaml to path/url')
#@click.option('--secrets', '-s', type=click.File(), help='secrets file')
def run(file, param, in_artifact, out_artifact, in_path, out_path, secrets, uid, name, workflow, save_to):
    """Execute a task and inject parameters."""

    meta = {}
    set_item(meta, uid, 'uid')
    set_item(meta, name, 'name')

    labels = {'parent_type': 'local', 'owner': getpass.getuser()}
    set_item(labels, workflow, 'workflow')
    meta['labels'] = labels

    spec = {}
    if param:
        params_dict = {}
        for param in param:
            i = param.find('=')
            if i == -1:
                continue
            key, value = param[:i].strip(), param[i + 1:].strip()
            if key is None:
                raise ValueError(f'cannot find param key in line ({param})')
            params_dict[key] = literal_eval(value)
        spec['parameters'] = params_dict

    set_item(spec, in_artifact, 'input_artifacts', line2keylist(in_artifact))
    set_item(spec, in_path, 'default_input_path')
    set_item(spec, out_path, 'default_output_path')
    set_item(spec, out_artifact, 'output_artifacts', line2keylist(out_artifact))
    set_item(spec, secrets, 'secret_sources', line2keylist(secrets, 'kind', 'source'))

    struct = {'metadata': meta, 'spec': spec}

    if '://' in file:
        secrets = SecretsStore()
        secrets.from_dict(spec)
        spec['secret_sources'] = secrets.to_serial()
        print(struct)
        remote_run(file, struct, save_to=save_to)
    else:
        os.environ['MLRUN_EXEC_CONFIG'] = json.dumps(struct)
        if not save_to:
            save_to = mktemp('.yaml')
            is_tmp = True
        else:
            is_tmp = False
        os.environ['MLRUN_META_FILEPATH'] = save_to
        try:
            with open(file) as fp:
                exec(fp.read())
            with open(save_to) as fp:
                print(fp.read())
            if is_tmp:
                os.remove(save_to)
        except FileNotFoundError as err:
            print(err)



def set_item(struct, item, key, value=None):
    if item:
        if value:
            struct[key] = value
        else:
            struct[key] = item


def line2keylist(lines: list, keyname='key', valname='path'):
    out = []
    for line in lines:
        i = line.find('=')
        if i == -1:
            raise ValueError('cannot find "=" in line ({}={})'.format(keyname, valname))
        key, value = line[:i].strip(), line[i + 1:].strip()
        if key is None:
            raise ValueError('cannot find key in line ({}={})'.format(keyname, valname))
        value = path.expandvars(value)
        out += [{keyname: key, valname: value}]
    return out


if __name__ == "__main__":
    main()


