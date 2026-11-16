package cn.minidayz.patcher;
import java.io.*;import java.util.zip.*;import org.json.*;
public final class CoreCli {
 interface Action{void run()throws Exception;}
 static void ok(boolean b,String title)throws Exception{if(!b)throw new Exception(title);System.out.println("PASS "+title);}
 static void rejects(Action a,String title)throws Exception{boolean rejected=false;try{a.run();}catch(IOException e){rejected=true;}ok(rejected,title);}
 public static void main(String[] args)throws Exception{
  ok(ReleaseOptions.resolveCode("",10,30,40)==41,"automatic version advances past installed and prior builds");
  ok(ReleaseOptions.resolveCode("100",10,30,40)==100,"explicit version code is applied");
  rejects(new Action(){public void run()throws Exception{ReleaseOptions.resolveCode("20",10,30,40);}},"downgrade is rejected");
  rejects(new Action(){public void run()throws Exception{ReleaseOptions.requestedCode("99999999999999999999999999");}},"overflow rejected without wrapping");
  rejects(new Action(){public void run()throws Exception{ReleaseOptions.requestedCode("0");}},"zero rejected");
  rejects(new Action(){public void run()throws Exception{ReleaseOptions.requestedCode("1.2");}},"noninteger rejected");
  rejects(new Action(){public void run()throws Exception{ReleaseOptions.nextCode(1,2100000000,0);}},"automatic code upper bound enforced");
  DiagnosticCli.Prefs p=new DiagnosticCli.Prefs();
  ok(OutputProvenance.state(p)==0,"legacy output is unknown");
  p.putBoolean("output_provenance_known",true).putBoolean("output_release_settings_known",true).putBoolean("previous_output_stale",false);
  for(String field:new String[]{"name","version","code"}){p.putString("release_"+field,"chosen");p.putString("output_requested_"+field,"chosen");}
  ok(OutputProvenance.state(p)==2,"matching output settings accepted");
  for(String field:new String[]{"name","version","code"}){p.putString("release_"+field,"edited");ok(OutputProvenance.state(p)==1,"changing "+field+" makes old result stale");p.putString("release_"+field,"chosen");}
  ok(OutputProvenance.state(p)==2,"restoring exact settings restores matching status");
  p.putBoolean("previous_output_stale",true);ok(OutputProvenance.state(p)==1,"input change remains stale even with matching version");
  JSONObject report=new JSONObject().put("status","success").put("stage","compatible");
  ok(BuildSteps.phase(report)==0,"inspection does not claim APK completion");
  ok(BuildSteps.phase(new JSONObject().put("stage","unity-engine"))==1,"resource phase displayed");
  ok(BuildSteps.phase(new JSONObject().put("stage","verify").put("status","failed"))==2,"failed verification never displays output success");
  ok(BuildSteps.phase(new JSONObject().put("stage","complete").put("status","success").put("signature_verified",true))==3,"verified output completes all phases");
  ok(!BuildView.render(new JSONObject().put("status","success").put("stage","imported")).contains("兼容性检查通过"),"file import cannot claim compatibility success");
  String redacted=LogText.redact("api_key=secret123\nAuthorization: Bearer abc.def\npassword: hidden123\n-----BEGIN PRIVATE KEY-----\nprivate123\n-----END PRIVATE KEY-----");
  ok(!redacted.contains("secret123")&&!redacted.contains("abc.def")&&!redacted.contains("hidden123")&&!redacted.contains("private123"),"log credentials and private keys redacted locally");
  StringBuilder large=new StringBuilder();for(int i=0;i<250000;i++)large.append("crash entry\n");
  ByteArrayOutputStream bytes=new ByteArrayOutputStream();ZipOutputStream zip=new ZipOutputStream(bytes);zip.putNextEntry(new ZipEntry("player.log"));zip.write(large.toString().getBytes("UTF-8"));zip.closeEntry();zip.close();
  ok(LogText.read(bytes.toByteArray()).contains(large.toString()),"multi-megabyte logs retained in full");
  rejects(new Action(){public void run()throws Exception{LogText.read(new byte[]{(byte)0xc3,0x28});}},"invalid UTF-8 gets explicit error");
  for(int i=5;i<args.length;i++){byte[] data=FilesEx.read(new FileInputStream(args[i]),4194304);ok(!LogBundleType.isInstallerDiagnostic(data)&&LogText.read(data).length()>0,"actual crash ZIP imported "+new File(args[i]).getName());}
  if(args.length>=5){
   File dir=new File(args[0]);dir.mkdirs();File apk=new File(args[1]),plugin=new File(args[2]),key=new File(args[3]);byte[] cert=FilesEx.read(new FileInputStream(args[4]),16384);
   String original=FilesEx.sha(apk,FilesEx.QUIET);FeaturePackages.importFile(plugin,dir,cert,FilesEx.QUIET);File module=new File(dir,"module.zip");PatchEngine engine=new PatchEngine(cert);
   ok(engine.inspect(apk,module,FilesEx.QUIET).profile!=null,"actual P14 plugin imports and matches game APK");
   File output=new File(dir,"generated.apk");ReleaseOptions release=new ReleaseOptions("核心版构建验证","1.5.5-coretest",2000000000);
   engine.build(apk,module,key,new File(dir,"work"),output,FilesEx.QUIET,null,release);Signing.verify(output,Signing.CERT_SHA,FilesEx.QUIET);FilesEx.verifyZip(output,FilesEx.QUIET);
   ZipFile result=new ZipFile(output);try{JSONObject receipt=new JSONObject(new String(FilesEx.read(result.getInputStream(result.getEntry("assets/diagnostics/build_info.json")),1048576),"UTF-8"));ok(receipt.getString("version").equals(release.version)&&receipt.getInt("version_code")==release.code,"build receipt records edited version");}finally{result.close();}
   ok(FilesEx.sha(apk,FilesEx.QUIET).equals(original),"original game APK unchanged");
   System.out.println("PASS full P14 rebuild, signing and archive verification");
  }
 }
}
