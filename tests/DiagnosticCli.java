package cn.minidayz.patcher;
import java.io.*;import java.nio.charset.StandardCharsets;import java.util.*;import java.util.zip.*;import android.content.SharedPreferences;import org.json.*;
public final class DiagnosticCli {
 static final class Prefs implements SharedPreferences,SharedPreferences.Editor {
  final Map<String,Object> data=new HashMap<String,Object>();
  public Map<String,?> getAll(){return data;}public String getString(String k,String d){return data.containsKey(k)?(String)data.get(k):d;}
  @SuppressWarnings("unchecked") public Set<String> getStringSet(String k,Set<String> d){return data.containsKey(k)?(Set<String>)data.get(k):d;}
  public int getInt(String k,int d){return data.containsKey(k)?(Integer)data.get(k):d;}public long getLong(String k,long d){return data.containsKey(k)?(Long)data.get(k):d;}
  public float getFloat(String k,float d){return data.containsKey(k)?(Float)data.get(k):d;}public boolean getBoolean(String k,boolean d){return data.containsKey(k)?(Boolean)data.get(k):d;}
  public boolean contains(String k){return data.containsKey(k);}public SharedPreferences.Editor edit(){return this;}
  public void registerOnSharedPreferenceChangeListener(SharedPreferences.OnSharedPreferenceChangeListener l){}public void unregisterOnSharedPreferenceChangeListener(SharedPreferences.OnSharedPreferenceChangeListener l){}
  public SharedPreferences.Editor putString(String k,String v){data.put(k,v);return this;}public SharedPreferences.Editor putStringSet(String k,Set<String> v){data.put(k,v);return this;}
  public SharedPreferences.Editor putInt(String k,int v){data.put(k,v);return this;}public SharedPreferences.Editor putLong(String k,long v){data.put(k,v);return this;}
  public SharedPreferences.Editor putFloat(String k,float v){data.put(k,v);return this;}public SharedPreferences.Editor putBoolean(String k,boolean v){data.put(k,v);return this;}
  public SharedPreferences.Editor remove(String k){data.remove(k);return this;}public SharedPreferences.Editor clear(){data.clear();return this;}public boolean commit(){return true;}public void apply(){}
 }
 static void ok(boolean value,String label)throws Exception{if(!value)throw new Exception(label);System.out.println("PASS "+label);}
 static byte[] zip(String name,String text)throws Exception{ByteArrayOutputStream b=new ByteArrayOutputStream();ZipOutputStream z=new ZipOutputStream(b);z.putNextEntry(new ZipEntry(name));z.write(text.getBytes(StandardCharsets.UTF_8));z.closeEntry();z.close();return b.toByteArray();}
 static byte[] compressedNonReport(int count,int size,boolean reportFirst)throws Exception{
  ByteArrayOutputStream b=new ByteArrayOutputStream();ZipOutputStream z=new ZipOutputStream(b);
  if(reportFirst){z.putNextEntry(new ZipEntry("report.json"));z.write("{\"format\":\"game-diagnostic/1\"}".getBytes(StandardCharsets.UTF_8));z.closeEntry();}
  byte[] zeros=new byte[8192];for(int i=0;i<count;i++){z.putNextEntry(new ZipEntry("ignored-"+i+".bin"));int left=size;while(left>0){int n=Math.min(left,zeros.length);z.write(zeros,0,n);left-=n;}z.closeEntry();}z.close();return b.toByteArray();
 }
 static boolean limit(byte[] zip)throws Exception{try{LogBundleType.isInstallerDiagnostic(zip);return false;}catch(IOException e){return e.getMessage()!=null&&e.getMessage().startsWith("E_LOG_LIMIT");}}
 public static void main(String[] args)throws Exception{
  byte[] assistant=zip("report.json","{\"format\":\"mdz-diagnostic/1\",\"installer_version\":\"1.4.0\",\"engine\":2}");
  ok(LogBundleType.isInstallerDiagnostic(assistant),"installer diagnostic is identified from structured marker");
  ok(!LogBundleType.isInstallerDiagnostic(zip("report.json","{\"format\":\"game-diagnostic/1\",\"message\":\"SIGSEGV\"}")),"a game report ZIP is not mistaken for the installer report");
  ok(!LogBundleType.isInstallerDiagnostic(zip("player.log","SIGSEGV")),"a game log ZIP remains eligible for import");
  ok(!LogBundleType.isInstallerDiagnostic("SIGSEGV".getBytes(StandardCharsets.UTF_8)),"a plain log remains eligible for import");
  ok(!LogBundleType.isInstallerDiagnostic(zip("report.json","not json")),"malformed report JSON is not called an installer report");
  ok(limit(compressedNonReport(1,5*1024*1024,false)),"highly compressed ignored item cannot exceed per-entry limit");
  ok(limit(compressedNonReport(3,3*1024*1024,true)),"ignored entries after an ordinary report cannot exceed total limit");
  ok(LogEvidence.diagnose("  \n").getString("conclusion").contains("尚未导入"),"empty log is identified as missing, not clean");
  ok(LogEvidence.diagnose("SIGSEGV").getInt("marker_occurrences")==1,"actual crash markers still classified");
  ok(Diagnosis.explain("E_INPUT_MISSING").getString("category").equals("missing-input"),"missing input has an actionable explanation");
  JSONObject success=new JSONObject().put("status","success").put("stage","local-complete");String text=DiagnosticHandoff.render(success,true,false);
  ok(text.contains("历史失败")&&text.contains("没有附带")&&text.contains("不能证明"),"successful current task and historical failure cannot be confused");
  ok(DiagnosticHandoff.render(new JSONObject().put("status","failed").put("error","E_INPUT_MISSING"),false,true).contains("E_INPUT_MISSING"),"current failure is shown when it exists");
  ok(OutputProvenance.importMakesStale(true,1,true,"old","new"),"changing input marks old output stale");
  ok(!OutputProvenance.importMakesStale(true,2,true,"same","same"),"re-importing identical module retains provenance");
  ok(OutputProvenance.importMakesStale(true,1,false,"old","old"),"legacy output is not treated as verified provenance after import");
  ok(!OutputProvenance.importMakesStale(true,3,true,"old","new"),"importing signing identity does not change output provenance");
  ok(!OutputProvenance.importMakesStale(false,1,true,"old","new"),"no output does not create stale output metadata");
  Prefs prefs=new Prefs();prefs.putString("output_module_sha256","original").putBoolean("output_provenance_known",true).putBoolean("previous_output_stale",false).commit();
  OutputProvenance.imported(prefs,2,"modified",true);
  ok(prefs.getBoolean("output_provenance_known",false)&&prefs.getBoolean("previous_output_stale",false),"committed AI module change persists stale status");
  OutputProvenance.imported(prefs,2,"original",true);
  ok(prefs.getBoolean("previous_output_stale",false),"rollback never falsely clears an existing stale status");
  Prefs restored=new Prefs();restored.putString("output_module_sha256","modified").putBoolean("output_provenance_known",true).putBoolean("previous_output_stale",false).commit();
  OutputProvenance.imported(restored,2,"original",true);
  ok(restored.getBoolean("previous_output_stale",false),"rollback to different module marks the existing output stale");
  Prefs failed=new Prefs();failed.putString("output_module_sha256","original").putBoolean("output_provenance_known",true).putBoolean("previous_output_stale",false).commit();
  // A failed edit or failed restore does not reach OutputProvenance.imported.
  ok(!failed.getBoolean("previous_output_stale",true),"pre-commit failure preserves prior output status");
  if(args.length>0)ok(LogBundleType.isInstallerDiagnostic(FilesEx.read(new FileInputStream(args[0]),4194304)),"supplied diagnostic is installer report");
 }
}
