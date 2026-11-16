"""Minimal Android binary XML/resources generator, preserving typed attributes."""
import struct,re
from pathlib import Path

def pool(strings):
 offsets=[];data=bytearray()
 def length(n):return bytes([n]) if n<128 else bytes([(n>>8)|128,n&255])
 for s in strings:
  raw=s.encode();offsets.append(len(data));data+=length(len(s.encode('utf-16le'))//2)+length(len(raw))+raw+b'\0'
 data+=bytes(-len(data)%4);start=28+4*len(strings)
 return struct.pack('<HHI5I',1,28,start+len(data),len(strings),0,256,start,0)+struct.pack('<'+'I'*len(offsets),*offsets)+data
class XML:
 def __init__(self,attrs):self.attrs=attrs;self.strings=[];self.nodes=[]
 def index(self,s):
  if s not in self.strings:self.strings.append(s)
  return self.strings.index(s)
 def start(self,tag,attrs={}):
  for k,v in attrs.items():self.index(k);self.index(str(v[1]) if v[0]==3 else k)
  self.index(tag);self.nodes.append(('start',tag,attrs))
 def end(self,tag):self.nodes.append(('end',tag,{}))
 def bytes(self,namespace=True):
  none=0xffffffff
  if namespace:ns=self.index('http://schemas.android.com/apk/res/android');pre=self.index('android')
  else:ns=none
  content=pool(self.strings)
  # Resource IDs align with string-pool indexes; only mapped attribute names get IDs.
  ids=[self.attrs.get(s,0) for s in self.strings];content+=struct.pack('<HHI',0x180,8,8+len(ids)*4)+struct.pack('<'+'I'*len(ids),*ids)
  if namespace:content+=struct.pack('<HHIIIII',0x100,16,24,1,none,pre,ns)
  for kind,tag,attrs in self.nodes:
   if kind=='end':content+=struct.pack('<HHIIIII',0x103,16,24,1,none,none,self.index(tag));continue
   ordered=sorted(attrs.items(),key=lambda p:self.attrs.get(p[0],0));data=struct.pack('<IIHHHHHH',none,self.index(tag),20,20,len(attrs),0,0,0)
   for k,(typ,val) in ordered:
    key=self.index(k);an=ns if k in self.attrs else none;raw=self.index(val) if typ==3 else none;v=self.index(val) if typ==3 else val
    data+=struct.pack('<IIIHBBI',an,key,raw,8,0,typ,v)
   content+=struct.pack('<HHIII',0x102,16,16+len(data),1,none)+data
  if namespace:content+=struct.pack('<HHIIIII',0x101,16,24,1,none,pre,ns)
  return struct.pack('<HHI',3,8,8+len(content))+content

def resources(package,paths):
 # One default XML type and one default drawable type, each with one entry.
 strings=[p[1] for p in paths];types=[p[0] for p in paths];keys=[p[2] for p in paths];tp=pool(types);kp=pool(keys)
 name=package.encode('utf-16le')+b'\0\0';header=bytearray(struct.pack('<HHII',0x200,288,0,0x7f)+name+bytes(256-len(name))+struct.pack('<5I',288,0,288+len(tp),0,0));body=bytearray(tp+kp)
 for i,p in enumerate(paths):
  tid=i+1;body+=struct.pack('<HHIBBHI',0x202,16,20,tid,0,0,1)+struct.pack('<I',0x40000000)
  config=struct.pack('<I',64)+bytes(60);entry=struct.pack('<HHI',8,0,i)+struct.pack('<HBBI',8,0,3,i)
  body+=struct.pack('<HHIBBHII',0x201,84,104,tid,0,0,1,88)+config+struct.pack('<I',0)+entry
 struct.pack_into('<I',header,4,len(header)+len(body));data=pool(strings)+header+body
 return struct.pack('<HHII',2,12,12+len(data),1)+data

def backup_rules():
 x=XML({});x.start('data-extraction-rules')
 for section in ['cloud-backup','device-transfer']:
  x.start(section)
  for d in ['root','file','database','sharedpref','external','device_root','device_file','device_database','device_sharedpref']:
   x.start('exclude',{'domain':(3,d),'path':(3,'.')});x.end('exclude')
  x.end(section)
 x.end('data-extraction-rules');return x.bytes(False)

def manifest(public):
 attrs={n:int(i,16) for n,i in re.findall(r'<public type="attr" name="([^"]+)" id="([^"]+)"',public)};x=XML(attrs)
 x.start('manifest',{'package':(3,'cn.minidayz.patcher'),'versionCode':(16,10700),'versionName':(3,'1.7.0')})
 x.start('uses-sdk',{'minSdkVersion':(16,26),'targetSdkVersion':(16,35)});x.end('uses-sdk')
 for permission in ['REQUEST_INSTALL_PACKAGES','FOREGROUND_SERVICE','FOREGROUND_SERVICE_DATA_SYNC','POST_NOTIFICATIONS']:
  x.start('uses-permission',{'name':(3,'android.permission.'+permission)});x.end('uses-permission')
 x.start('queries')
 for p in ['com.mdz21.minidayz2.xin.p13i','com.mdz21.minidayz2.xin.diag','com.mdz21.minidayz2']:
  x.start('package',{'name':(3,p)});x.end('package')
 x.end('queries')
 theme=re.search(r'<public type="style" name="Theme.Material.Light.NoActionBar" id="([^"]+)"',public)
 assert theme
 x.start('application',{'label':(3,'P版补丁助手'),'icon':(1,0x7f020000),'theme':(1,int(theme[1],16)),'allowBackup':(18,0),'fullBackupContent':(18,0),'restoreAnyVersion':(18,0),'dataExtractionRules':(1,0x7f010000),'usesCleartextTraffic':(18,0),'debuggable':(18,0)})
 x.start('activity',{'name':(3,'cn.minidayz.patcher.MainActivity'),'exported':(18,1)})
 x.start('intent-filter');x.start('action',{'name':(3,'android.intent.action.MAIN')});x.end('action');x.start('category',{'name':(3,'android.intent.category.LAUNCHER')});x.end('category');x.end('intent-filter');x.end('activity')
 x.start('service',{'name':(3,'cn.minidayz.patcher.BuildService'),'exported':(18,0),'foregroundServiceType':(17,1)});x.end('service')
 x.start('provider',{'name':(3,'cn.minidayz.patcher.OutputProvider'),'authorities':(3,'cn.minidayz.patcher.files'),'exported':(18,0),'grantUriPermissions':(18,1)});x.end('provider');x.end('application');x.end('manifest');return x.bytes()
