"""Create a signed, exact-input CDC delta pack. Never embeds signing keys."""
import sys,json,hashlib,zipfile,copy,argparse,subprocess,os
from pathlib import Path
from fastcdc import fastcdc
from cryptography import x509
from cryptography.hazmat.primitives import serialization,hashes
from cryptography.hazmat.primitives.asymmetric import padding
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT.parent
parser=argparse.ArgumentParser();parser.add_argument('--key',type=Path,required=True);parser.add_argument('--input',type=Path,action='append',required=True);parser.add_argument('--target',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument("--content-match",action="store_true",help="Sign full inventories for engine 2 content matching");args=parser.parse_args();KEY=args.key
pem=KEY.read_bytes();private=serialization.load_pem_private_key(pem,password=None);cert=x509.load_pem_x509_certificate(pem[pem.index(b'-----BEGIN CERTIFICATE-----'):]);fp=cert.fingerprint(hashes.SHA256()).hex();assert fp=='21fa47120af53f71b39e886eaf0d71a159c34a2d332646a1cf0820a59549ad10'
(ROOT/'assets/trust.der').write_bytes(cert.public_bytes(serialization.Encoding.DER))
out=args.output or ROOT/('output/MiniDayZ2_P14_Modules_1.1.0.zip' if args.content_match else 'output/MiniDayZ2_P14_Modules_1.0.0.zip');out.parent.mkdir(parents=True,exist_ok=True);blobdata={};delta_cache={}
sha=lambda b:hashlib.sha256(b).hexdigest()
def sig(n):
 n=n.upper();return n.startswith('META-INF/') and n.endswith(('.SF','.RSA','.DSA','.EC','MANIFEST.MF'))
def blob(b):
 h=sha(b);name='payload/'+h;blobdata.setdefault(name,b);return name
def delta(before,after):
 key=sha(before),sha(after)
 if key in delta_cache:return copy.deepcopy(delta_cache[key])
 if before==after:return None
 commands=[]
 if len(before)<32768 or len(after)<32768:commands=[{'data':blob(after)}]
 else:
  old={sha(before[c.offset:c.offset+c.length]):(c.offset,c.length) for c in fastcdc(before,min_size=8192,avg_size=32768,max_size=131072)}
  for c in fastcdc(after,min_size=8192,avg_size=32768,max_size=131072):
   data=after[c.offset:c.offset+c.length];match=old.get(sha(data))
   if match and before[match[0]:match[0]+match[1]]==data:
    if commands and 'copy' in commands[-1] and sum(commands[-1]['copy'])==match[0]:commands[-1]['copy'][1]+=match[1]
    else:commands.append({'copy':list(match)})
   else:commands.append({'data':blob(data)})
 result={'before_sha256':key[0],'before_size':len(before),'after_sha256':key[1],'after_size':len(after),'commands':commands};delta_cache[key]=copy.deepcopy(result);return result
# ZIP metadata differs across Android/JVM builds. Entry-content hashes are the
# authoritative postconditions; the input whole-APK hash still selects profile.
def operations(a,b):
 result=[]
 with zipfile.ZipFile(a) as old,zipfile.ZipFile(b) as new:
  on={x for x in old.namelist() if not sig(x)};nn={x for x in new.namelist() if not sig(x)};assert on<=nn,'Deletion requires a newer schema'
  for n in sorted(nn):
   if n.endswith('/'):continue
   oi=old.getinfo(n) if n in on else None;ni=new.getinfo(n)
   if oi and oi.CRC==ni.CRC and oi.file_size==ni.file_size:continue
   before=old.read(n) if oi else b'';after=new.read(n);op=delta(before,after)
   if op:
    op={'entry':n,**op}
    if not oi:op['create']=True
    result.append(op)
 return result
fixes=WORK/'inputs/MiniDayZ2_0.1.53_P13_Fixes.apk';isol=WORK/'source/output/MiniDayZ2_0.1.53_P13_Isolated.apk';card=WORK/'source/output/MiniDayZ2_0.1.53_P13_Coexist.apk';p14=WORK/'source/output/MiniDayZ2_0.1.53_P14_Coexist.apk';target=args.target or WORK/'source/output/MiniDayZ2_0.1.53_P14_InfoFix.apk'
inputs=[('p13-fixes','P13 修复版 → P14 完整隔离共存版',fixes),('p13-isolated','P13 隔离基础版 → P14',isol),('p13-card','P13 物品卡片版 → P14',card),('p14-007','P14 首版物品信息崩溃修复',p14),('p14-current','校验当前 P14-info-009',target)]
if args.input:inputs=[('custom-'+sha(p.read_bytes())[:12],p.name+' → 已适配目标',p) for p in args.input]
identity_ops=operations(fixes,isol) if not args.input else [];feature_ops=operations(isol,target) if not args.input else [];profiles=[]
from androguard.core.axml import AXMLPrinter
from loguru import logger
logger.remove()
with zipfile.ZipFile(target) as z:
 xml=AXMLPrinter(z.read('AndroidManifest.xml')).get_xml_obj();ns='{http://schemas.android.com/apk/res/android}';assert xml.get('package')=='com.mdz21.minidayz2.xin.p13i';version=xml.get(ns+'versionName');version_code=int(xml.get(ns+'versionCode'))
if args.content_match:
 cp=os.pathsep.join([str(ROOT/'build/classes'),str(ROOT/'toolchain/json.jar')])
 subprocess.run(['java','-jar',str(ROOT/'toolchain/ecj.jar'),'-8','-warn:none','-cp',cp,'-d',str(ROOT/'build/classes'),str(ROOT/'tools/InventoryCli.java')],check=True)
for ident,name,src in inputs:
 print('Profile:',ident,flush=True)
 modules=[{'id':'isolation-core','name':'完整隔离共存基础','mandatory':True,'depends_on':[],'operations':identity_ops if src==fixes else []},{'id':'p14-features','name':('P14 全功能整合与物品信息修复' if not args.input else version+' 整合适配'),'mandatory':True,'depends_on':['isolation-core'],'operations':feature_ops if not args.input and src in [fixes,isol] else operations(src,target)}]
 profiles.append({'id':ident,'name':name,'input_sha256':sha(src.read_bytes()),'output_package':'com.mdz21.minidayz2.xin.p13i','output_version':version,'output_version_code':version_code,'modules':modules})
if args.content_match:
 for profile,(_,_,src) in zip(profiles,inputs):
  raw_inventory=subprocess.check_output(['java','-Xmx128m','-cp',cp,'cn.minidayz.patcher.InventoryCli',str(src)])
  profile['input_inventory']=json.loads(raw_inventory)
  assert 'identity' in profile['input_inventory']['AndroidManifest.xml'],'manifest cannot be normalized'
  with zipfile.ZipFile(src) as z:profile['input_manifest_payload']=blob(z.read('AndroidManifest.xml'))
module={'format' :'mdz-patch/1','engine_min':(2 if args.content_match else 1),'id':('minidayz.p14.complete' if not args.input else 'minidayz.custom.complete'),'name':('MiniDayZ2 P14 完整隔离共存整合包' if not args.input else 'MiniDayZ2 '+version+' 完整共存整合包'),'version':(('1.1.0' if args.content_match else '1.0.0')+' / '+('P14-info-009' if not args.input else version)),'signer_sha256':fp,'profiles':profiles,'payloads':{n:{'size':len(b),'sha256':sha(b)} for n,b in sorted(blobdata.items())}}
raw=json.dumps(module,ensure_ascii=False,separators=(',',':')).encode();signature=private.sign(raw,padding.PKCS1v15(),hashes.SHA256())
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 z.writestr('module.json',raw);z.writestr('module.sig',signature)
 for n,b in sorted(blobdata.items()):z.writestr(n,b)
 z.writestr('README.txt','P版补丁助手模块包。支持 module.json 登记输入；引擎2清单还允许已签名全量指纹一致的重打包和名称版本修改。未知作者新版需适配后增加档案。\n包含完整隔离共存基础及当前P14整合功能，不包含密钥。\n模块由现有P版签名身份签名；不执行脚本。\n独立单功能模块拆分与未知新版自动识别尚未完成。\n')
print('Created',out,'bytes',out.stat().st_size,'payloads',len(blobdata),'profiles',len(profiles),flush=True)
((ROOT/'tests/module_inventory.json') if not args.output else out.with_suffix('.inventory.json')).write_text(json.dumps({'module_sha256':sha(out.read_bytes()),'profiles':[{'id':p['id'],'sha256':p['input_sha256'],'operations':sum(len(m['operations']) for m in p['modules'])} for p in profiles],'payload_bytes':sum(map(len,blobdata.values()))},indent=2))
