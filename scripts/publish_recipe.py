import json,html,re,hashlib,pathlib,uuid,argparse,os
units={'GRAMS':'g','MILLS':'ml','KGS':'kg','ITEM':'','CUP':'cup','TEASPOON':'tsp','TABLESPOON':'tbsp','PINCH':'pinch'}
def num(x):return str(int(x)) if float(x).is_integer() else str(x)
def ingredient(i):
 q=i.get('quantity'); n=i['ingredient']['name']
 if not q:return n
 a=num(q['amount']);a+=('–'+num(q['secondaryAmount'])) if 'secondaryAmount'in q else ''
 u=units[q['quantityType']];return ' '.join(x for x in [a,u,n] if x)
css=':root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#faf6ee;color:#28352d;font:20px/1.6 system-ui,-apple-system,sans-serif}main{max-width:900px;margin:auto;padding:32px 24px 64px}header{border-bottom:2px solid #c7a75d;padding-bottom:20px}h1{font-size:clamp(30px,5vw,46px);line-height:1.2}h2{font-size:28px}h3{font-size:23px}a{color:#315c45}li{padding:9px 0}.eyebrow{font-size:14px;letter-spacing:.12em;text-transform:uppercase}.meta,footer{font-size:16px;color:#526359}footer{border-top:1px solid #d9d1c1;margin-top:32px;padding-top:18px}input{font:inherit;padding:12px;width:100%;border:1px solid #718575;border-radius:8px;margin:16px 0}.cards{list-style:none;padding:0}.cards li{border-bottom:1px solid #ded8cb}.cards a{display:block;padding:10px 0;font-weight:600}a:focus-visible,input:focus-visible{outline:3px solid #a37824;outline-offset:4px}'
def page(title,body,data=None):
 script='<script type="application/ld+json">'+json.dumps(data,ensure_ascii=False).replace('<','\\u003c')+'</script>' if data else ''
 return '<!doctype html><html lang="en-AU"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>'+html.escape(title)+'</title>'+script+'<style>'+css+'</style></head><body><main>'+body+'</main></body></html>'

def render_recipe(d):
 name=d['name']
 ings=[ingredient(i) for i in sorted(d['ingredients'],key=lambda x:x['order'])]; steps=sorted(d['steps'],key=lambda x:x['order'])
 instr=[]; current=None; method='';opened=False;number=1
 for s in steps:
  if s.get('isSection'):
   current={'@type':'HowToSection','name':s['step'],'itemListElement':[]};instr.append(current)
   if opened:method+='</ol>'
   method+='<h3>'+html.escape(s['step'])+'</h3><ol start="'+str(number)+'">';opened=True
  else:
   step={'@type':'HowToStep','text':s['step']}
   (current['itemListElement'] if current else instr).append(step)
   if not opened:method+='<ol>';opened=True
   method+='<li>'+html.escape(s['step'])+'</li>';number+=1
 if opened:method+='</ol>'
 data={'@context':'https://schema.org','@type':'Recipe','name':name,'recipeIngredient':ings,'recipeInstructions':instr}
 meta=[]
 if d.get('serves'):data['recipeYield']=str(d['serves']);meta.append('Yield: '+str(d['serves'])+' (as saved)')
 # Preserve source duration fields without inventing totals: Crouton duration is preparation time.
 if d.get('duration'):data['prepTime']='PT'+num(d['duration'])+'M';meta.append('Prep: '+num(d['duration'])+' min')
 if d.get('cookingDuration'):data['cookTime']='PT'+num(d['cookingDuration'])+'M';meta.append('Cook: '+num(d['cookingDuration'])+' min')
 source=''
 if d.get('sourceName'):source='Source credited in Crouton: '+html.escape(d['sourceName'])+'. '
 if d.get('webLink','').startswith('https://'):source+='<a href="'+html.escape(d['webLink'],quote=True)+'">Original recipe</a>.';data['isBasedOn']=d['webLink']
 body='<a href="index.html">← All recipes</a><article><header><p class="eyebrow">TRCH · Kitchen collection</p><h1>'+html.escape(name)+'</h1><p class="meta">'+' · '.join(meta)+'</p></header><h2>Ingredients</h2><ul>'+''.join('<li>'+html.escape(i)+'</li>' for i in ings)+'</ul><h2>Method</h2>'+method+'<footer>'+source+' Ingredients and method preserved from the supplied Crouton export. Photos omitted.</footer></article>'
 return page(name+' · TRCH',body,data)

def digest(text): return hashlib.sha256(text.encode()).hexdigest()

def validate(d):
    if not isinstance(d,dict): raise ValueError('Expected one native Crouton recipe object')
    key=str(uuid.UUID(d['uuid'])).lower()
    if not isinstance(d.get('name'),str) or not d['name'].strip(): raise ValueError('Missing name')
    for field in ('ingredients','steps'):
        if not isinstance(d.get(field),list) or not d[field]: raise ValueError('Missing '+field)
        if len({x['order'] for x in d[field]}) != len(d[field]): raise ValueError('Ambiguous duplicate ordering in '+field)
    for item in d['ingredients']:
        if not isinstance(item['ingredient']['name'],str): raise ValueError('Invalid ingredient')
        if item.get('quantity'):
            q=item['quantity']
            if q['quantityType'] not in units: raise ValueError('Unsupported quantity unit '+q['quantityType'])
            for k in ('amount','secondaryAmount'):
                if k in q and (not isinstance(q[k],(int,float)) or not __import__('math').isfinite(q[k])): raise ValueError('Invalid quantity')
    if not any(not x.get('isSection') for x in d['steps']): raise ValueError('No method steps')
    for step in d['steps']:
        if not isinstance(step.get('step'),str) or not step['step'].strip(): raise ValueError('Empty method step')
    # This renderer only emits explicit public recipe fields. Images, notes and
    # app metadata in the input are never copied into generated files.
    return key

def plan(recipe, root):
    key=validate(recipe)
    manifest_path=root/'recipe-registry.json'
    registry=json.loads(manifest_path.read_text())
    if registry.get('version')!=1: raise ValueError('Unsupported registry version')
    entries=registry['recipes']; paths=set()
    for id,entry in entries.items():
        if str(uuid.UUID(id)).lower()!=id: raise ValueError('Invalid registry identity')
        path=entry['path']
        if not re.fullmatch(r'[a-z0-9-]+\.html',path) or path in paths: raise ValueError('Unsafe or duplicate path')
        paths.add(path)
        if digest((root/path).read_text())!=entry['sha256']: raise ValueError('Page changed outside publisher: '+path)
    index=(root/'index.html').read_text()
    if digest(index)!=registry['index_sha256']: raise ValueError('Index changed outside publisher; reconcile before updating')
    content=render_recipe(recipe)
    if key in entries:
        raise ValueError('Recipe already published; add-only mode leaves it unchanged')
    slug=re.sub('[^a-z0-9]+','-',recipe['name'].lower()).strip('-') or 'recipe'
    path=slug+'-'+key+'.html'
    if path in paths or (root/path).exists(): raise ValueError('Path collision')
    entries[key]={'name':recipe['name'],'path':path,'sha256':digest(content)}
    links=''.join('<li><a href="'+e['path']+'">'+html.escape(e['name'])+'</a></li>' for e in sorted(entries.values(),key=lambda x:x['name'].casefold()))
    index,n=re.subn(r'(<ul class="cards">).*?(</ul>)',lambda m:m[1]+links+m[2],index,count=1,flags=re.S)
    if n!=1: raise ValueError('Missing index list')
    index=re.sub(r'<p id="count" class="meta">.*?</p>','<p id="count" class="meta">'+str(len(entries))+' recipes</p>',index,count=1)
    index=index.replace('Ten recipes from your Crouton export, ready to browse on HomeView.','Recipes from Crouton, ready to browse on HomeView.')
    index=index.replace('Snapshot of the supplied export dated 13 November 2026, not an automatic sync or a confirmed complete Crouton library.','Recipes published individually from Crouton. This is not an automatic sync or a confirmed complete Crouton library.')
    registry['index_sha256']=digest(index)
    return {path:content,'index.html':index,'recipe-registry.json':json.dumps(registry,indent=2,ensure_ascii=False)+'\n'}, {'status':'added','uuid':key,'path':path}

def main():
    p=argparse.ArgumentParser(description='Stage one Crouton recipe update; never publish credentials, images, or raw exports.')
    p.add_argument('recipe',type=pathlib.Path);p.add_argument('--repo',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True)
    a=p.parse_args()
    if a.output.resolve()==a.repo.resolve(): p.error('Output must be a separate staging directory')
    changes,result=plan(json.loads(a.recipe.read_text()),a.repo)
    if a.output.exists() and any(a.output.iterdir()): p.error('Output directory must be empty')
    a.output.mkdir(parents=True,exist_ok=True)
    for name,content in changes.items(): (a.output/name).write_text(content)
    print(json.dumps({**result,'changed_files':list(changes)},indent=2))
if __name__=='__main__': main()
