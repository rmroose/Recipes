"""Build immutable recipe inbox into an add-only site. Standard library only."""
import json, pathlib, shutil, sys
from publish_recipe import plan, validate, digest

def process(root):
    root=pathlib.Path(root)
    status={}
    for source in sorted((root/'incoming').glob('*.json')):
        try:
            if source.is_symlink() or source.stat().st_size>1000000: raise ValueError('Invalid input file')
            recipe=json.loads(source.read_text())
            key=validate(recipe)
            if source.stem.lower()!=key: raise ValueError('Filename does not match recipe UUID')
            registry=json.loads((root/'recipe-registry.json').read_text())
            if key in registry['recipes']:
                entry=registry['recipes'][key]
                if digest((root/entry['path']).read_text())!=entry['sha256']: raise ValueError('Existing recipe changed; reconcile manually')
                status[key]={'state':'published','path':entry['path'],'mode':'add-only; existing recipe retained'}
                continue
            changes,result=plan(recipe,root)
            for path,content in changes.items(): (root/path).write_text(content)
            status[key]={'state':'published','path':result['path']}
        except (ValueError,KeyError,TypeError,OSError) as e:
            status[source.stem]={'state':'error','message':str(e)}
    # Check whole registry, including index, even for runs with no new recipes.
    registry=json.loads((root/'recipe-registry.json').read_text())
    if digest((root/'index.html').read_text())!=registry['index_sha256']: raise ValueError('Index changed outside publisher')
    for entry in registry['recipes'].values():
        if digest((root/entry['path']).read_text())!=entry['sha256']: raise ValueError('Recipe changed outside publisher')
    (root/'publish-status.json').write_text(json.dumps(status,indent=2)+'\n')
    return status

if __name__=='__main__':
    root=pathlib.Path.cwd()
    process(root)
    # Explicit publication allowlist: no inbox, script, registry, token or raw export.
    output=root/'_site'
    if output.exists(): shutil.rmtree(output)
    output.mkdir()
    for path in root.glob('*.html'): shutil.copyfile(path,output/path.name)
    shutil.copyfile(root/'publish-status.json',output/'publish-status.json')
