package cn.minidayz.patcher;

import android.app.*;
import android.content.*;
import android.content.pm.PackageInfo;
import android.database.Cursor;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.*;
import android.view.*;
import android.widget.*;
import org.json.*;
import java.io.*;

/** File-first offline installer. Local files and explicit build actions. */
public final class MainActivity extends Activity implements Jobs.Listener {
 private StudioUi ui;
 private Jobs jobs;
 private int page,ink,muted;
 private LinearLayout body,home,taskPage,tools;
 private TextView source,module,key,engineLabel,featuresLabel,next,status,taskStatus,detail,result,buildWindow,logSummary,releasePreview;
 private TextView[] phases=new TextView[4];
 private EditText releaseName,releaseVersion,releaseCode;
 private ProgressBar bar;
 private Button pickApk,pickModule,pickKey,pickEngine,check,build,install,save,diagnose,cancel,featureButton,copyLog;
 private String cachedApkDetails="",cachedApkName="",cachedFeatureIdentity="",cachedFeatureText="";
 private static final int SAVE_APK=20,SAVE_LOG=21,IMPORT_GAME_LOG=64;

 @Override public void onCreate(Bundle state){
  super.onCreate(state);requestWindowFeature(Window.FEATURE_NO_TITLE);
  jobs=Jobs.get(this);ui=new StudioUi(this);ink=ui.ink;muted=ui.muted;
  page=state==null?getIntent().getIntExtra("studio_tab",0):state.getInt("page",0);
  body=ui.mount(page,new StudioUi.Nav(){public void select(int tab){showPage(tab);}});
  home=column(body);taskPage=column(body);tools=column(body);

  LinearLayout intro=ui.card(home,"本次制作","原版 APK + 插件包 → 新的游戏安装包");
  next=text("",14,ink);next.setTypeface(null,Typeface.BOLD);intro.addView(next);

  LinearLayout inputs=ui.card(home,"01  添加文件","支持完整 APK、插件总包与单功能 ZIP。");
  source=text("",14,muted);source.setTextIsSelectable(true);inputs.addView(source);
  pickApk=button(inputs,"+ 添加游戏安装包",false,new View.OnClickListener(){public void onClick(View v){pick(1);}});
  module=text("",14,muted);module.setTextIsSelectable(true);inputs.addView(module);
  pickModule=button(inputs,"+ 导入插件包",false,new View.OnClickListener(){public void onClick(View v){pick(2);}});
  featuresLabel=text("",13,muted);inputs.addView(featuresLabel);
  featureButton=button(inputs,"管理已导入功能",false,new View.OnClickListener(){public void onClick(View v){chooseFeatures();}});

  LinearLayout options=ui.card(home,"02  名称与版本","留空使用默认值。内部版本代码自动递增，也可手动指定。");
  releaseName=entry(options,"显示名称","MiniDayZ2 共存版","release_name",false);
  releaseVersion=entry(options,"版本号","例如 1.5.5-P14","release_version",false);
  LinearLayout codeBox=collapsible(options,"内部版本代码","Android 用它判断更新顺序；必须高于已安装版本和上次生成版本。",false);
  releaseCode=entry(codeBox,"版本代码（可选）","自动递增","release_code",true);
  releasePreview=text("",12,muted);options.addView(releasePreview);

  LinearLayout config=collapsible(home,"构建配置 · 签名与数据引擎","签名用于生成可安装 APK。只有包含数据规则的插件才需要外置引擎。",false);
  key=text("",13,muted);config.addView(key);
  pickKey=button(config,"导入签名 PEM / 交接 ZIP",false,new View.OnClickListener(){public void onClick(View v){pick(3);}});
  engineLabel=text("",13,muted);config.addView(engineLabel);
  pickEngine=button(config,"导入数据引擎 ZIP（按需）",false,new View.OnClickListener(){public void onClick(View v){pick(4);}});

  LinearLayout generate=ui.card(home,"03  检查并生成","生成前检查输入匹配、插件签名和版本参数。");
  status=text("",14,ink);generate.addView(status);
  build=button(generate,"检查并生成 APK",true,new View.OnClickListener(){public void onClick(View v){startBuild();}});
  check=button(generate,"先检查兼容性",false,new View.OnClickListener(){public void onClick(View v){
   jobs.begin("检查兼容性",new Jobs.Work(){public void run(Jobs j)throws Exception{j.inspect();}});
  }});
  detail=text("",12,muted);detail.setTextIsSelectable(true);generate.addView(detail);
  button(generate,"打开可视化任务窗口 →",false,new View.OnClickListener(){public void onClick(View v){showPage(1);}});

  LinearLayout output=ui.card(home,"04  安装与导出","");
  result=text("",14,muted);result.setTextIsSelectable(true);output.addView(result);
  install=button(output,"安装生成的 APK",true,new View.OnClickListener(){public void onClick(View v){install();}});
  save=button(output,"导出 APK 到文件夹",false,new View.OnClickListener(){public void onClick(View v){saveAs(false);}});

  LinearLayout progress=ui.card(taskPage,"当前任务","任务可在后台继续，返回这里查看结果。");
  taskStatus=text("",16,ink);taskStatus.setTextIsSelectable(true);progress.addView(taskStatus);
  bar=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);progress.addView(bar,new LinearLayout.LayoutParams(-1,dp(7)));
  progress.addView(text("百分比表示当前步骤，不是整包总进度。",11,muted));
  String[] labels={"1  校验输入与插件","2  应用功能与处理资源","3  签名与验证安装包","4  输出成功，可安装或导出"};
  for(int i=0;i<4;i++){phases[i]=text(labels[i],14,muted);phases[i].setPadding(dp(12),dp(10),dp(8),dp(10));progress.addView(phases[i]);}
  cancel=button(progress,"取消当前任务",false,new View.OnClickListener(){public void onClick(View v){jobs.cancel=true;jobs.status="正在安全取消…";jobs.notifyUi();}});
  LinearLayout window=ui.card(taskPage,"实时记录","可上下滚动、长按选择，也可复制完整记录。");
  final ScrollView monitor=new ScrollView(this);buildWindow=text("尚未开始任务",12,ink);buildWindow.setTypeface(Typeface.MONOSPACE);buildWindow.setTextIsSelectable(true);
  monitor.setBackgroundDrawable(ui.shape(ui.bg,10));monitor.setPadding(dp(10),dp(8),dp(10),dp(8));monitor.addView(buildWindow);
  window.addView(monitor,new LinearLayout.LayoutParams(-1,dp(300)));
  monitor.setOnTouchListener(new View.OnTouchListener(){public boolean onTouch(View v,android.view.MotionEvent e){v.getParent().requestDisallowInterceptTouchEvent(e.getAction()!=android.view.MotionEvent.ACTION_UP&&e.getAction()!=android.view.MotionEvent.ACTION_CANCEL);return false;}});
  copyLog=button(window,"复制任务记录",false,new View.OnClickListener(){public void onClick(View v){android.content.ClipboardManager clipboard=(android.content.ClipboardManager)getSystemService(CLIPBOARD_SERVICE);clipboard.setPrimaryClip(ClipData.newPlainText("P Patcher 任务记录",buildWindow.getText()));Toast.makeText(MainActivity.this,"任务记录已复制",Toast.LENGTH_SHORT).show();}});
  button(window,"返回制作页面",false,new View.OnClickListener(){public void onClick(View v){showPage(0);}});

  LinearLayout diagnosis=ui.card(tools,"诊断与反馈","保留失败原因和输入指纹，方便定位打包问题。");
  diagnose=button(diagnosis,"导出安装器诊断 ZIP",false,new View.OnClickListener(){public void onClick(View v){saveAs(true);}});
  LinearLayout logs=ui.card(tools,"游戏运行日志","可选导入系统崩溃日志或游戏诊断包；仅保存并附加到诊断导出。");
  logSummary=text("",13,muted);logs.addView(logSummary);
  button(logs,"导入游戏日志 ZIP / TXT",false,new View.OnClickListener(){public void onClick(View v){pick(IMPORT_GAME_LOG);}});
  button(logs,"清空已导入日志",false,new View.OnClickListener(){public void onClick(View v){if(jobs.busy)return;new File(jobs.root,"game-log.txt").delete();new File(jobs.root,"game-log-meta.json").delete();jobs.status="已清空导入日志";changed();}});
  LinearLayout maintenance=ui.card(tools,"本机文件","清理未完成任务产生的临时缓存。");
  button(maintenance,"清理构建临时缓存",false,new View.OnClickListener(){public void onClick(View v){if(jobs.busy)return;jobs.begin("清理临时缓存",new Jobs.Work(){public void run(Jobs j)throws Exception{FilesEx.deleteTree(new File(j.root,"jobs"));new File(j.root,"import.pending").delete();j.stage("cleanup","临时缓存已清理，输入与成功结果已保留");}});}});
  tools.addView(text("P Patcher 1.7.0 · 核心版\n本机处理 / Android 8.0+ / 完整单 APK",12,muted));
  showPage(page);jobs.listen(this);
 }

 private void startBuild(){
  final String n=releaseName.getText().toString(),v=releaseVersion.getText().toString(),c=releaseCode.getText().toString();
  try{ReleaseOptions.requestedCode(c);}catch(Exception e){releaseCode.setError(e.getMessage());Toast.makeText(this,e.getMessage(),Toast.LENGTH_LONG).show();return;}
  jobs.begin("开始本地构建",new Jobs.Work(){public void run(Jobs j)throws Exception{j.build(n,v,c);}});showPage(1);
 }
 @Override protected void onSaveInstanceState(Bundle state){state.putInt("page",page);super.onSaveInstanceState(state);}
 @Override public void onDestroy(){jobs.detach(this);super.onDestroy();}
 @Override public void onResume(){super.onResume();if(jobs!=null)jobs.listen(this);}
 int dp(int n){return ui.dp(n);}
 TextView text(String s,int size,int color){return ui.text(s,size,color);}
 Button button(LinearLayout parent,String label,boolean primary,View.OnClickListener click){return ui.button(parent,label,primary,click);}
 private LinearLayout column(LinearLayout parent){LinearLayout l=new LinearLayout(this);l.setOrientation(1);parent.addView(l,new LinearLayout.LayoutParams(-1,-2));return l;}
 private LinearLayout collapsible(LinearLayout parent,final String title,String description,boolean open){
  LinearLayout card=ui.card(parent,"","");final LinearLayout content=new LinearLayout(this);content.setOrientation(1);
  final Button toggle=button(card,title+(open?"  −":"  +"),false,null);card.addView(content,new LinearLayout.LayoutParams(-1,-2));
  content.addView(text(description,12,muted));content.setVisibility(open?View.VISIBLE:View.GONE);
  toggle.setOnClickListener(new View.OnClickListener(){public void onClick(View v){boolean show=content.getVisibility()!=View.VISIBLE;content.setVisibility(show?View.VISIBLE:View.GONE);toggle.setText(title+(show?"  −":"  +"));}});return content;
 }
 void showPage(int tab){page=Math.max(0,Math.min(2,tab));ui.select(page);home.setVisibility(page==0?View.VISIBLE:View.GONE);taskPage.setVisibility(page==1?View.VISIBLE:View.GONE);tools.setVisibility(page==2?View.VISIBLE:View.GONE);ui.scrollToTop();}
 @Override protected void onNewIntent(Intent i){super.onNewIntent(i);setIntent(i);showPage(i.getIntExtra("studio_tab",0));}
 EditText entry(LinearLayout parent,String title,String hint,final String pref,boolean number){
  parent.addView(text(title,13,ink));final EditText e=new EditText(this);e.setSingleLine(true);e.setHint(hint);e.setFilters(new android.text.InputFilter[]{new android.text.InputFilter.LengthFilter(number?10:80)});
  if(number)e.setInputType(android.text.InputType.TYPE_CLASS_NUMBER);e.setText(getSharedPreferences("local",0).getString(pref,""));parent.addView(e,new LinearLayout.LayoutParams(-1,-2));ui.field(e);
  e.addTextChangedListener(new android.text.TextWatcher(){public void beforeTextChanged(CharSequence s,int a,int c,int f){}public void afterTextChanged(android.text.Editable x){}public void onTextChanged(CharSequence s,int a,int b,int c){getSharedPreferences("local",0).edit().putString(pref,s.toString()).apply();if(result!=null)changed();}});return e;
 }
 private String size(File f){return android.text.format.Formatter.formatShortFileSize(this,f.length());}
 private String apkDetails(){
  if(!jobs.file(1).isFile())return "尚未添加 APK";
  String identity=jobs.apkName+":"+jobs.file(1).length()+":"+jobs.file(1).lastModified();
  if(!identity.equals(cachedApkName)){cachedApkName=identity;cachedApkDetails="";try{PackageInfo p=getPackageManager().getPackageArchiveInfo(jobs.file(1).getPath(),0);if(p!=null)cachedApkDetails="\n"+p.versionName+" · 版本代码 "+p.versionCode+"\n"+p.packageName;}catch(Exception ignored){}}
  return jobs.apkName+" · "+size(jobs.file(1))+cachedApkDetails;
 }
 public void changed(){
  if(source==null||releaseCode==null)return;
  boolean hasApk=jobs.file(1).isFile(),hasModule=jobs.file(2).isFile(),idle=!jobs.busy;
  source.setText(apkDetails());module.setText(hasModule?jobs.moduleName+"\n"+size(jobs.file(2)):"尚未导入插件包");
  key.setText(jobs.keyReady?"✓ 签名已就绪 · 已在本机核验":"○ 尚未导入签名文件");
  engineLabel.setText(jobs.file(4).isFile()?"✓ 数据引擎："+getSharedPreferences("local",0).getString("engine_name",""):"○ 未导入数据引擎 · 普通补丁包不需要");
  featuresLabel.setText(featureList());
  String hint=jobs.busy?"正在处理 · 可切到任务窗口查看":!hasApk?"下一步：添加原版游戏安装包":!hasModule?"下一步：导入对应版本的插件包":!jobs.keyReady?"下一步：展开构建配置，导入签名文件":"已准备好 · 确认版本后即可生成";
  next.setText(hint);status.setText(jobs.status+(jobs.progress.length()>0?"\n"+jobs.progress:""));taskStatus.setText(status.getText());
  detail.setText(jobs.plan==null?"输入尚未检查。":jobs.plan.profile.optString("name")+"\n目标："+jobs.plan.profile.optString("output_package")+"\n"+(jobs.plan.matchMode.equals("exact")?"✓ 输入指纹匹配":"✓ 逐文件校验通过"));
  releasePreview.setText("将生成："+(releaseName.getText().toString().trim().length()==0?"MiniDayZ2 共存版":releaseName.getText().toString().trim())+" · "+(releaseVersion.getText().toString().trim().length()==0?(jobs.plan==null?"插件默认版本":jobs.plan.profile.optString("output_version")):releaseVersion.getText().toString().trim()));
  JSONObject r=jobs.busy&&!jobs.buildTask?jobs.report:jobs.buildReport;
  buildWindow.setText(BuildView.render(r));updatePhases(r);
  boolean numeric=jobs.buildTask&&jobs.progress.contains("%");bar.setIndeterminate(jobs.busy&&!numeric);bar.setMax(100);
  try{bar.setProgress(numeric?Integer.parseInt(jobs.progress.substring(0,jobs.progress.indexOf("%"))):r.optBoolean("signature_verified")?100:0);}catch(Exception ignored){}
  cancel.setVisibility(jobs.busy?View.VISIBLE:View.GONE);cancel.setEnabled(!jobs.cancel);
  releaseName.setEnabled(idle);releaseVersion.setEnabled(idle);releaseCode.setEnabled(idle);
  pickApk.setEnabled(idle);pickModule.setEnabled(idle);pickKey.setEnabled(idle);pickEngine.setEnabled(idle);featureButton.setEnabled(idle&&hasModule);
  check.setEnabled(idle&&hasApk&&hasModule);build.setEnabled(idle&&hasApk&&hasModule&&jobs.keyReady);
  boolean has=jobs.output!=null&&jobs.output.isFile();install.setEnabled(idle&&has);save.setEnabled(idle&&has);diagnose.setEnabled(idle);
  for(Button b:new Button[]{pickApk,pickModule,pickKey,pickEngine,featureButton,check,build,install,save,diagnose})b.setAlpha(b.isEnabled()?1f:.45f);
  result.setText(has?jobs.outputLabel+"\n"+size(jobs.output)+" · "+(outputState()==2?"与当前文件及版本设置一致":"设置或输入已变化，请重新生成"):"尚无生成结果。成功后可直接安装或导出。");
  logSummary.setText("尚未导入游戏日志");try{JSONObject m=new JSONObject(new String(FilesEx.read(new FileInputStream(new File(jobs.root,"game-log-meta.json")),65536),"UTF-8"));logSummary.setText(m.optString("name")+"\n"+m.optInt("characters")+" 字符 · 仅供排查参考");}catch(Exception ignored){}
 }
 private void updatePhases(JSONObject r){
  int phase=r.length()==0?-1:BuildSteps.phase(r);boolean inspected="success".equals(r.optString("status"))&&r.has("profile")&&!r.optBoolean("signature_verified");boolean failed="failed".equals(r.optString("status"));boolean success=r.optBoolean("signature_verified")&&"success".equals(r.optString("status"));
  String[] labels={"校验输入与插件","应用功能与处理资源","签名与验证安装包","输出成功，可安装或导出"};
  for(int i=0;i<4;i++){boolean done=success||i<phase||(inspected&&i==0);boolean active=!success&&!inspected&&i==phase;phases[i].setText((done?"✓  ":active?(failed?"×  ":"●  "):"○  ")+labels[i]);phases[i].setTextColor(active&&failed?0xffbd4b43:done||active?ui.accent:muted);phases[i].setBackgroundDrawable(ui.shape(active?ui.line:ui.card,9));}
 }
 String featureList(){String identity=jobs.file(2).length()+":"+jobs.file(2).lastModified();if(identity.equals(cachedFeatureIdentity))return cachedFeatureText;try{JSONArray list=FeaturePackages.inventory(jobs.root);int enabled=0;for(int i=0;i<list.length();i++)if(list.getJSONObject(i).getBoolean("enabled"))enabled++;cachedFeatureText=list.length()==0?"导入后可查看功能选择":"已启用 "+enabled+" / "+list.length()+" 个功能包 · 基础包始终保留";cachedFeatureIdentity=identity;return cachedFeatureText;}catch(Exception e){return "功能清单暂不可用："+e.getMessage();}}
 int outputState(){return OutputProvenance.state(getSharedPreferences("local",0));}
 void chooseFeatures(){if(jobs.busy)return;try{final JSONArray list=FeaturePackages.inventory(jobs.root);final java.util.ArrayList<String> ids=new java.util.ArrayList<String>();java.util.ArrayList<String> names=new java.util.ArrayList<String>();java.util.ArrayList<Boolean> enabled=new java.util.ArrayList<Boolean>();for(int i=0;i<list.length();i++){JSONObject f=list.getJSONObject(i);if(f.getString("id").equals("isolation-core"))continue;ids.add(f.getString("id"));names.add(f.getString("name"));enabled.add(f.getBoolean("enabled"));}if(ids.size()==0){Toast.makeText(this,"请先导入插件总包或数据功能 ZIP",Toast.LENGTH_LONG).show();return;}final boolean[] checked=new boolean[ids.size()];for(int i=0;i<checked.length;i++)checked[i]=enabled.get(i);new AlertDialog.Builder(this).setTitle("选择功能 · 基础包始终启用").setMultiChoiceItems(names.toArray(new String[0]),checked,new DialogInterface.OnMultiChoiceClickListener(){public void onClick(DialogInterface d,int which,boolean value){checked[which]=value;}}).setNegativeButton("取消",null).setPositiveButton("保存选择",new DialogInterface.OnClickListener(){public void onClick(DialogInterface d,int which){jobs.begin("保存功能选择",new Jobs.Work(){public void run(Jobs j)throws Exception{FeaturePackages.select(j.root,ids,checked,FilesEx.read(getAssets().open("trust.der"),16384),j);j.plan=null;getSharedPreferences("local",0).edit().putBoolean("previous_output_stale",true).commit();j.stage("features","功能选择已保存，请重新生成 APK");}});}}).show();}catch(Exception e){Toast.makeText(this,e.getMessage(),Toast.LENGTH_LONG).show();}}
 void pick(int kind){if(jobs.busy)return;Intent i=new Intent("android.intent.action.OPEN_DOCUMENT");i.addCategory(Intent.CATEGORY_OPENABLE);i.setType("*/*");i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|64);try{startActivityForResult(i,kind);}catch(Exception e){Toast.makeText(this,"无法打开系统文件选择器",Toast.LENGTH_LONG).show();}}
 String display(Uri uri){Cursor c=null;try{c=getContentResolver().query(uri,new String[]{"_display_name"},null,null,null);if(c!=null&&c.moveToFirst())return c.getString(0);}catch(Exception ignored){}finally{if(c!=null)c.close();}return "已选择文件";}
 void confirmPreviousOutput(final boolean saving){
  if(outputState()==2){if(saving)saveAsNow(false);else installNow();return;}
  String detail=outputState()==1?"文件、功能选择或版本设置已变化，上次成功结果使用的是较早的设置。":"这是旧版本保留的结果，无法确认它对应当前输入。";
  new AlertDialog.Builder(this).setTitle("上次成功结果")
   .setMessage(detail+"建议先返回重新生成。若你确认需要此前结果，也可以继续。")
   .setNegativeButton("返回重新生成",null).setPositiveButton(saving?"继续保存旧结果":"继续安装旧结果",new DialogInterface.OnClickListener(){public void onClick(DialogInterface d,int w){
    if(saving)saveAsNow(false);else installNow();
   }}).show();
 }
 void saveAs(boolean logs){if(jobs.busy)return;if(logs)saveAsNow(true);else confirmPreviousOutput(true);}
 void saveAsNow(boolean logs){Intent i=new Intent("android.intent.action.CREATE_DOCUMENT");i.addCategory(Intent.CATEGORY_OPENABLE);i.setType(logs?"application/zip":"application/vnd.android.package-archive");i.putExtra(Intent.EXTRA_TITLE,logs?"MDZ_诊断_"+System.currentTimeMillis()+".zip":(jobs.output==null?"MiniDayZ2_共存版.apk":jobs.output.getName()));try{startActivityForResult(i,logs?SAVE_LOG:SAVE_APK);}catch(Exception e){Toast.makeText(this,"无法打开保存位置",Toast.LENGTH_LONG).show();}}
 @Override protected void onActivityResult(final int request,int code,Intent data){
  super.onActivityResult(request,code,data);if(code!=RESULT_OK||data==null||data.getData()==null)return;final Uri uri=data.getData();
  if(request==IMPORT_GAME_LOG){final String name=display(uri);jobs.begin("读取游戏日志",new Jobs.Work(){public void run(Jobs j)throws Exception{GameLogs.importLog(j,uri,name);}});return;}
  if(request>=1&&request<=4){try{getContentResolver().getClass().getMethod("takePersistableUriPermission",Uri.class,int.class).invoke(getContentResolver(),uri,1);}catch(Exception ignored){}
   final String name=display(uri);jobs.begin("导入文件",new Jobs.Work(){public void run(Jobs j)throws Exception{j.importFile(uri,request,name);}});
  }else if(request==SAVE_APK||request==SAVE_LOG)jobs.exportTask(new Jobs.Work(){public void run(Jobs j)throws Exception{j.export(uri,request==SAVE_LOG);}});
 }
 void install(){if(!jobs.busy)confirmPreviousOutput(false);}
 void installNow(){try{
  if(Build.VERSION.SDK_INT>=26){boolean allowed=(Boolean)getPackageManager().getClass().getMethod("canRequestPackageInstalls").invoke(getPackageManager());
   if(!allowed){startActivity(new Intent("android.settings.MANAGE_UNKNOWN_APP_SOURCES",Uri.parse("package:"+getPackageName())));Toast.makeText(this,"允许此来源后，返回点击安装",Toast.LENGTH_LONG).show();return;}}
  Uri uri=Uri.parse("content://cn.minidayz.patcher.files/latest.apk");Intent i=new Intent(Intent.ACTION_VIEW);i.setDataAndType(uri,"application/vnd.android.package-archive");i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);i.setClipData(ClipData.newRawUri("P版构建结果",uri));startActivity(i);
 }catch(Exception e){Toast.makeText(this,"无法打开安装界面，可先另存 APK 再安装",Toast.LENGTH_LONG).show();}}
}
