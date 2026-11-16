package cn.minidayz.patcher;

import android.app.*;
import android.content.*;
import android.database.Cursor;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.*;
import android.view.*;
import android.widget.*;
import org.json.*;
import java.io.*;

/** Guided installation, with diagnostic and repair tools available separately. */
public final class MainActivity extends Activity implements Jobs.Listener {
 private StudioUi ui;
 private Jobs jobs;
 private int page,ink,muted;
 private LinearLayout body,home,tools;
 private TextView source,module,key,engineLabel,featuresLabel,next,status,taskStatus,detail,result,buildWindow,structure,logSummary,localSummary;
 private EditText releaseName,releaseVersion;
 private ProgressBar bar;
 private Button pickApk,pickModule,pickKey,pickEngine,check,build,install,save,diagnose,cancel;
 private PatchEngine.Plan featurePlan;
 private String featureText="";
 private static final int SAVE_APK=20,SAVE_LOG=21,IMPORT_GAME_LOG=64;

 @Override public void onCreate(Bundle state){
  super.onCreate(state);requestWindowFeature(Window.FEATURE_NO_TITLE);
  jobs=Jobs.get(this);ui=new StudioUi(this);ink=ui.ink;muted=ui.muted;
  page=getIntent().getIntExtra("studio_tab",0);
  body=ui.mount(page,new StudioUi.Nav(){public void select(int tab){
   showPage(tab==1?2:0);
  }});
  home=column(body);tools=column(body);

  LinearLayout intro=ui.card(home,"插件安装","导入文件 → 查看功能 → 生成 APK → 安装。只在手机本机处理。");
  next=text("",15,ink);next.setTypeface(null,Typeface.BOLD);intro.addView(next);

  LinearLayout inputs=ui.card(home,"1  导入文件","首次使用导入以下四项。以后更新某个功能，只需重新导入它的单独 ZIP。");
  source=text("",14,muted);inputs.addView(source);
  pickApk=button(inputs,"选择游戏 APK",false,new View.OnClickListener(){public void onClick(View v){pick(1);}});
  module=text("",14,muted);inputs.addView(module);
  pickModule=button(inputs,"导入插件总包 / 单功能 ZIP",false,new View.OnClickListener(){public void onClick(View v){pick(2);}});
  engineLabel=text("",14,muted);inputs.addView(engineLabel);
  pickEngine=button(inputs,"导入引擎 ZIP",false,new View.OnClickListener(){public void onClick(View v){pick(4);}});
  key=text("",14,muted);inputs.addView(key);
  pickKey=button(inputs,"选择签名 PEM 或交接 ZIP",false,new View.OnClickListener(){public void onClick(View v){pick(3);}});

  LinearLayout featureCard=ui.card(home,"2  功能清单","勾选本次要装的功能。已导入不等于已安装；成功生成后，安装输出 APK 才会生效。");
  featuresLabel=text("尚未导入功能包",14,muted);featureCard.addView(featuresLabel);
  button(featureCard,"选择本次安装的功能",false,new View.OnClickListener(){public void onClick(View v){chooseFeatures();}});
  LinearLayout generate=ui.card(home,"3  生成 APK","生成时会自动检查插件与游戏是否匹配。想先查看结果，可单独检查兼容性。");
  build=button(generate,"检查并生成 APK",true,new View.OnClickListener(){public void onClick(View v){
   final String name=releaseName.getText().toString(),version=releaseVersion.getText().toString();
   getSharedPreferences("local",0).edit().putString("release_name",name).putString("release_version",version).commit();
   jobs.begin("开始本地构建",new Jobs.Work(){public void run(Jobs j)throws Exception{j.build(name,version);}});
  }});
  check=button(generate,"仅检查兼容性",false,new View.OnClickListener(){public void onClick(View v){
   jobs.begin("检查兼容性",new Jobs.Work(){public void run(Jobs j)throws Exception{j.inspect();}});
  }});
  status=text("",14,ink);status.setTextIsSelectable(true);generate.addView(status);
  bar=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);
  generate.addView(bar,new LinearLayout.LayoutParams(-1,dp(6)));
  detail=text("",13,muted);detail.setTextIsSelectable(true);generate.addView(detail);
  cancel=button(generate,"取消当前任务",false,new View.OnClickListener(){public void onClick(View v){
   jobs.cancel=true;jobs.status="正在安全取消…";jobs.notifyUi();
  }});
  button(generate,"查看详细进度与问题处理",false,new View.OnClickListener(){public void onClick(View v){showPage(2);}});

  LinearLayout options=collapsible(home,"可选：自定义显示名称和版本","留空使用插件默认版本；这些选项不会更改包名。",false);
  releaseName=entry(options,"游戏显示名称","MiniDayZ2 共存版","release_name");
  releaseVersion=entry(options,"游戏版本名称","留空使用插件版本","release_version");

  LinearLayout output=ui.card(home,"4  安装或保存","生成成功后打开系统安装界面。安装前请备份需要保留的游戏存档。");
  result=text("",14,muted);output.addView(result);
  install=button(output,"安装上次成功生成的 APK",true,new View.OnClickListener(){public void onClick(View v){install();}});
  save=button(output,"另存上次成功的 APK",false,new View.OnClickListener(){public void onClick(View v){saveAs(false);}});

  LinearLayout progress=ui.card(tools,"任务状态","这里显示当前任务和最近一次检查或构建的详细记录。");
  taskStatus=text("",15,ink);taskStatus.setTextIsSelectable(true);progress.addView(taskStatus);
  LinearLayout logBox=collapsible(progress,"查看构建详情","可滚动或长按复制；输出状态以实际结果为准。",false);
  ScrollView monitor=new ScrollView(this);buildWindow=text("尚未开始检查",13,ink);
  buildWindow.setTypeface(Typeface.MONOSPACE);buildWindow.setTextIsSelectable(true);
  monitor.setBackgroundColor(ui.dark?0xff101b26:0xfff2f6f8);monitor.addView(buildWindow);
  logBox.addView(monitor,new LinearLayout.LayoutParams(-1,dp(260)));
  monitor.setOnTouchListener(new View.OnTouchListener(){public boolean onTouch(View v,android.view.MotionEvent e){
   v.getParent().requestDisallowInterceptTouchEvent(e.getAction()!=android.view.MotionEvent.ACTION_UP);return false;
  }});
  diagnose=button(progress,"导出安装器诊断 ZIP",false,new View.OnClickListener(){public void onClick(View v){saveAs(true);}});
  progress.addView(text("如果游戏运行时闪退，请另从游戏内导出诊断；这里导出的是安装器记录。",12,muted));

  LinearLayout logs=collapsible(tools,"游戏闪退或运行错误","先在游戏内导出诊断 ZIP，再导入这里，一起包含在安装器诊断中。",false);
  logSummary=text("尚未导入游戏诊断包。",13,muted);logs.addView(logSummary);
  button(logs,"导入游戏诊断 ZIP",false,new View.OnClickListener(){public void onClick(View v){pick(IMPORT_GAME_LOG);}});
  button(logs,"清空已导入游戏日志",false,new View.OnClickListener(){public void onClick(View v){
   if(jobs.busy)return;new File(jobs.root,"game-log.txt").delete();new File(jobs.root,"game-log-meta.json").delete();
   logSummary.setText("尚未导入游戏诊断包。");jobs.status="已清空导入的日志";changed();
  }});

  structure=text("",13,muted);localSummary=text("",13,muted);
  LinearLayout maintenance=collapsible(tools,"其他工具","清理只针对未完成的构建缓存。",false);
  button(maintenance,"清理未完成的构建缓存",false,new View.OnClickListener(){public void onClick(View v){
   if(jobs.busy)return;FilesEx.deleteTree(new File(jobs.root,"jobs"));new File(jobs.root,"import.pending").delete();
   Toast.makeText(MainActivity.this,"已清理临时文件，输入、密钥及成功结果保留",Toast.LENGTH_LONG).show();
  }});
  tools.addView(text("支持 Android 8.0+ 和完整单 APK。未知新版需要对应适配包。",12,muted));
  showPage(page);jobs.listen(this);
  if(Build.VERSION.SDK_INT>=33&&!getPreferences(0).getBoolean("asked_notifications",false)){
   getPreferences(0).edit().putBoolean("asked_notifications",true).commit();
   try{Activity.class.getMethod("requestPermissions",String[].class,int.class).invoke(this,new Object[]{new String[]{"android.permission.POST_NOTIFICATIONS"},90});}catch(Exception ignored){}
  }
 }

 private LinearLayout column(LinearLayout parent){LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.VERTICAL);parent.addView(l,new LinearLayout.LayoutParams(-1,-2));return l;}
 /** A real button controls visibility; content starts collapsed and is still accessible. */
 private LinearLayout collapsible(LinearLayout parent,final String title,String description,boolean initiallyOpen){
  LinearLayout card=ui.card(parent,"","");final LinearLayout content=new LinearLayout(this);content.setOrientation(LinearLayout.VERTICAL);
  final Button toggle=button(card,"",false,null);card.addView(content,new LinearLayout.LayoutParams(-1,-2));
  if(description.length()>0)content.addView(text(description,13,muted));
  content.setVisibility(initiallyOpen?View.VISIBLE:View.GONE);toggle.setText(title+(initiallyOpen?"  ▲":"  ▼"));
  toggle.setOnClickListener(new View.OnClickListener(){public void onClick(View v){
   boolean open=content.getVisibility()!=View.VISIBLE;content.setVisibility(open?View.VISIBLE:View.GONE);toggle.setText(title+(open?"  ▲":"  ▼"));
  }});return content;
 }
 private void confirmRepair(){
  if(jobs.busy)return;new AlertDialog.Builder(this).setTitle("保存实测结论")
   .setMessage("请确认你已安装最近修复对应的 APK，进入游戏复现原问题并验证通过。打包成功不能代替此步骤。")
   .setNegativeButton("尚未实测",null).setPositiveButton("实测通过",new DialogInterface.OnClickListener(){public void onClick(DialogInterface d,int w){
    jobs.begin("记录实测修复规则",new Jobs.Work(){public void run(Jobs j)throws Exception{
     new RepairRules(j.root).confirmLatest(FilesEx.sha(j.file(2),j));j.stage("rule-confirmed","实测结论已记录，相同输入可在本地复用");
    }});
   }}).show();
 }
 private void confirmLogAssociation(){
  if(jobs.busy)return;new AlertDialog.Builder(this).setTitle("确认日志归属")
   .setMessage("仅在确定日志来自当前 APK 或它生成的游戏版本时确认。APK、插件或日志变化后声明失效；已有冲突不能被覆盖。")
   .setNegativeButton("不确定",null).setPositiveButton("确认来源",new DialogInterface.OnClickListener(){public void onClick(DialogInterface d,int w){
    jobs.begin("记录日志归属",new Jobs.Work(){public void run(Jobs j)throws Exception{LogAssociation.confirm(j);}});
   }}).show();
 }

 @Override public void onDestroy(){jobs.detach(this);super.onDestroy();}
 @Override public void onResume(){super.onResume();if(jobs!=null)jobs.listen(this);}
 int dp(int n){return (int)(getResources().getDisplayMetrics().density*n+.5f);}
 TextView text(String s,int size,int color){TextView t=new TextView(this);t.setText(s);t.setTextSize(size);t.setTextColor(color);t.setPadding(0,dp(4),0,dp(7));t.setLineSpacing(dp(2),1f);return t;}
 void showPage(int tab){page=tab==2?2:0;ui.select(page==2?1:0);home.setVisibility(page==0?View.VISIBLE:View.GONE);tools.setVisibility(page==2?View.VISIBLE:View.GONE);ui.scrollToTop();}
 @Override protected void onNewIntent(Intent i){super.onNewIntent(i);setIntent(i);showPage(i.getIntExtra("studio_tab",0));}
 EditText entry(LinearLayout parent,String title,String hint,final String pref){
  parent.addView(text(title,14,ink));EditText e=new EditText(this);e.setTextSize(16);e.setTextColor(ink);e.setHintTextColor(muted);e.setSingleLine(true);e.setHint(hint);
  e.setFilters(new android.text.InputFilter[]{new android.text.InputFilter.LengthFilter(80)});e.setText(getSharedPreferences("local",0).getString(pref,""));
  parent.addView(e,new LinearLayout.LayoutParams(-1,-2));ui.field(e);e.addTextChangedListener(new android.text.TextWatcher(){
   public void beforeTextChanged(CharSequence s,int a,int c,int f){}public void onTextChanged(CharSequence s,int a,int b,int c){getSharedPreferences("local",0).edit().putString(pref,s.toString()).apply();}public void afterTextChanged(android.text.Editable e){}
  });return e;
 }
 Button button(LinearLayout parent,String label,boolean primary,View.OnClickListener click){return ui.button(parent,label,primary,click);}

 public void changed(){
  if(source==null)return;ui.select(page==2?1:0);
  boolean hasApk=jobs.file(1).isFile(),hasModule=jobs.file(2).isFile();
  source.setText(hasApk?"已选择游戏："+jobs.apkName:"未选择游戏 APK");
  module.setText(hasModule?"已选择插件："+jobs.moduleName:"未选择插件 ZIP");
  engineLabel.setText(jobs.file(4).isFile()?"已导入引擎："+getSharedPreferences("local",0).getString("engine_name",""):"未导入引擎 ZIP（数据功能需要）");
  pickEngine.setEnabled(!jobs.busy);
  featuresLabel.setText(featureList());
  key.setText(jobs.keyReady?"已导入签名文件 · 生成时会再次核验":"未导入签名文件");
  String hint=jobs.busy?"正在处理，请等待完成。":!hasApk?"下一步：选择游戏 APK。":!hasModule?"下一步：选择对应版本的插件 ZIP。":!jobs.file(4).isFile()?"下一步：导入配套引擎 ZIP。":!jobs.keyReady?"下一步：导入原 P 版签名文件。":"文件已准备，可检查并生成 APK。";
  next.setText(hint);String task=jobs.status+(jobs.progress.length()>0?"  "+jobs.progress:"");status.setText(task);taskStatus.setText("当前状态："+task+"\n以下详情是最近一次检查或构建，可能早于当前任务。");
  String d="";if(jobs.plan!=null)try{
   d="已匹配："+jobs.plan.profile.getString("name")+"\n目标版本："+jobs.plan.profile.getString("output_version")+"\n"+(jobs.plan.matchMode.equals("exact")?"输入完整校验匹配":"已通过逐文件兼容校验");
   d+=featureSummary(jobs.plan);
  }catch(Exception ignored){}else{featurePlan=null;featureText="";}detail.setText(d);
  buildWindow.setText(BuildView.render(jobs.buildTask?jobs.report:jobs.buildReport));
  boolean numeric=jobs.buildTask&&jobs.progress.contains("%");bar.setIndeterminate(jobs.busy&&!numeric);bar.setMax(100);
  try{bar.setProgress(numeric?Integer.parseInt(jobs.progress.substring(0,jobs.progress.indexOf("%"))):jobs.buildReport.optString("status").equals("success")?100:0);}catch(Exception ignored){}
  cancel.setVisibility(jobs.busy?View.VISIBLE:View.GONE);boolean idle=!jobs.busy;
  releaseName.setEnabled(idle);releaseVersion.setEnabled(idle);if(jobs.plan!=null)releaseVersion.setHint(jobs.plan.profile.optString("output_version"));
  pickApk.setEnabled(idle);pickModule.setEnabled(idle);pickKey.setEnabled(idle);check.setEnabled(idle&&hasApk&&hasModule);build.setEnabled(idle&&hasApk&&hasModule&&jobs.keyReady);
  boolean has=jobs.output!=null&&jobs.output.isFile();install.setEnabled(idle&&has);save.setEnabled(idle&&has);diagnose.setEnabled(idle);
  for(Button b:new Button[]{pickApk,pickModule,pickKey,pickEngine,check,build,install,save,diagnose})b.setAlpha(b.isEnabled()?1f:.42f);
  int outputState=outputState();String origin=outputState==2?"已确认对应当前输入":outputState==1?"输入已更换，建议先重新生成":"来源尚未确认，建议先重新生成";
  result.setText(has?"上次成功结果："+jobs.outputLabel+"\n"+origin+"。":"还没有成功生成的 APK。");
  try{JSONObject local=new JSONObject(new String(FilesEx.read(new FileInputStream(new File(jobs.root,"local-assistant.json")),1048576),"UTF-8"));localSummary.setText("最近诊断（输入或日志变化后请重新运行）\n"+LocalAssistant.render(local));}catch(Exception ignored){}
  try{JSONObject meta=new JSONObject(new String(FilesEx.read(new FileInputStream(new File(jobs.root,"game-log-meta.json")),65536),"UTF-8"));logSummary.setText("已导入："+meta.optString("name")+"\n日志文本："+meta.optInt("characters")+" 字符");}catch(Exception ignored){}
  try{JSONObject analysis=new JSONObject(new String(FilesEx.read(new FileInputStream(new File(jobs.root,"project-analysis.json")),524288),"UTF-8"));structure.setText("最近分析（更换 APK 后请重新分析）\n引擎："+analysis.optString("engine")+" · 条目："+analysis.optInt("entries")+"\n文本候选："+analysis.getJSONArray("text_candidates").length());}catch(Exception ignored){}
 }

 /** Display only a bounded summary from the module whose signature was checked. */
 String featureSummary(PatchEngine.Plan plan){
  if(featurePlan==plan)return featureText;
  featurePlan=plan;
  try{
   JSONObject assistant=plan.module.optJSONObject("assistant");
   JSONArray provided=assistant==null?null:assistant.optJSONArray("features");
   JSONArray items=FeatureGuide.describe(plan.module,plan.profile);
   StringBuilder s=new StringBuilder("\n\n插件说明（插件声明，功能仍需游戏测试）：");
   if(provided==null||provided.length()==0)s.append("\n此插件未提供功能说明，以下仅为模块名称。");
   for(int i=0;i<items.length();i++){
    JSONObject item=items.getJSONObject(i);
    String name=shortText(item.optString("name",item.optString("module_id","未命名模块")),48);
    String description=shortText(item.optString("description",""),100);
    s.append("\n• ").append(name.length()==0?"未命名模块":name);
    if(provided!=null&&provided.length()>0&&description.length()>0)s.append("：").append(description);
   }
   if(items.length()==0)s.append("\n没有可显示的功能说明。");

   featureText=s.toString();
  }catch(Exception e){featureText="\n\n插件说明暂不可显示；功能仍需游戏测试。";}
  return featureText;
 }
 String shortText(String value,int limit){String clean=value.replace('\n',' ').replace('\r',' ').trim();if(clean.length()<=limit)return clean;int end=Character.isHighSurrogate(clean.charAt(limit-1))?limit-1:limit;return clean.substring(0,end)+"…";}

 String featureList(){try{JSONArray list=FeaturePackages.inventory(jobs.root);StringBuilder s=new StringBuilder();for(int i=0;i<list.length();i++){JSONObject f=list.getJSONObject(i);s.append(f.getBoolean("enabled")?"☑ 待生成  ":"☐ 未启用  ").append(f.getString("name")).append("\n");}return list.length()==0?"尚未导入功能包":s.toString()+"\n当前输出："+(jobs.output==null?"尚未生成":outputState()==2?"已按当前选择生成，安装后生效":"选择已变化，请重新生成");}catch(Exception e){return "功能清单读取失败："+e.getMessage();}}
 void chooseFeatures(){if(jobs.busy)return;try{final JSONArray list=FeaturePackages.inventory(jobs.root);final java.util.ArrayList<String> ids=new java.util.ArrayList<String>();java.util.ArrayList<String> names=new java.util.ArrayList<String>();java.util.ArrayList<Boolean> enabled=new java.util.ArrayList<Boolean>();for(int i=0;i<list.length();i++){JSONObject f=list.getJSONObject(i);if(f.getString("id").equals("isolation-core"))continue;ids.add(f.getString("id"));names.add(f.getString("name"));enabled.add(f.getBoolean("enabled"));}if(ids.size()==0){Toast.makeText(this,"请先导入插件总包或数据功能 ZIP",Toast.LENGTH_LONG).show();return;}final boolean[] checked=new boolean[ids.size()];for(int i=0;i<checked.length;i++)checked[i]=enabled.get(i);new AlertDialog.Builder(this).setTitle("选择功能 · 基础包始终启用").setMultiChoiceItems(names.toArray(new String[0]),checked,new DialogInterface.OnMultiChoiceClickListener(){public void onClick(DialogInterface d,int which,boolean value){checked[which]=value;}}).setNegativeButton("取消",null).setPositiveButton("保存选择",new DialogInterface.OnClickListener(){public void onClick(DialogInterface d,int which){jobs.begin("保存功能选择",new Jobs.Work(){public void run(Jobs j)throws Exception{FeaturePackages.select(j.root,ids,checked,FilesEx.read(getAssets().open("trust.der"),16384),j);j.plan=null;getSharedPreferences("local",0).edit().putBoolean("previous_output_stale",true).commit();j.stage("features","功能选择已保存，请重新生成 APK");}});}}).show();}catch(Exception e){Toast.makeText(this,e.getMessage(),Toast.LENGTH_LONG).show();}}
 void pick(int kind){if(jobs.busy)return;Intent i=new Intent("android.intent.action.OPEN_DOCUMENT");i.addCategory(Intent.CATEGORY_OPENABLE);i.setType("*/*");i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|64);try{startActivityForResult(i,kind);}catch(Exception e){Toast.makeText(this,"无法打开系统文件选择器",Toast.LENGTH_LONG).show();}}
 String display(Uri uri){Cursor c=null;try{c=getContentResolver().query(uri,new String[]{"_display_name"},null,null,null);if(c!=null&&c.moveToFirst())return c.getString(0);}catch(Exception ignored){}finally{if(c!=null)c.close();}return "已选择文件";}
 /** 0 = unknown historical provenance, 1 = previous input, 2 = current input. */
 int outputState(){android.content.SharedPreferences p=getSharedPreferences("local",0);return !p.getBoolean("output_provenance_known",false)?0:p.getBoolean("previous_output_stale",true)?1:2;}
 void confirmPreviousOutput(final boolean saving){
  if(outputState()==2){if(saving)saveAsNow(false);else installNow();return;}
  String detail=outputState()==1?"游戏或插件已更换，上次成功结果使用的是较早的输入。":"这是旧版本保留的结果，无法确认它对应当前输入。";
  new AlertDialog.Builder(this).setTitle("上次成功结果")
   .setMessage(detail+"建议先返回重新生成。若你确认需要此前结果，也可以继续。")
   .setNegativeButton("返回重新生成",null).setPositiveButton(saving?"继续保存旧结果":"继续安装旧结果",new DialogInterface.OnClickListener(){public void onClick(DialogInterface d,int w){
    if(saving)saveAsNow(false);else installNow();
   }}).show();
 }
 void saveAs(boolean logs){if(logs)saveAsNow(true);else confirmPreviousOutput(true);}
 void saveAsNow(boolean logs){Intent i=new Intent("android.intent.action.CREATE_DOCUMENT");i.addCategory(Intent.CATEGORY_OPENABLE);i.setType(logs?"application/zip":"application/vnd.android.package-archive");i.putExtra(Intent.EXTRA_TITLE,logs?"MDZ_诊断_"+System.currentTimeMillis()+".zip":(jobs.output==null?"MiniDayZ2_共存版.apk":jobs.output.getName()));try{startActivityForResult(i,logs?SAVE_LOG:SAVE_APK);}catch(Exception e){Toast.makeText(this,"无法打开保存位置",Toast.LENGTH_LONG).show();}}
 @Override protected void onActivityResult(final int request,int code,Intent data){
  super.onActivityResult(request,code,data);if(code!=RESULT_OK||data==null||data.getData()==null)return;final Uri uri=data.getData();
  if(request==IMPORT_GAME_LOG){final String name=display(uri);jobs.begin("读取游戏日志",new Jobs.Work(){public void run(Jobs j)throws Exception{GameLogs.importLog(j,uri,name);}});return;}
  if(request>=1&&request<=4){try{getContentResolver().getClass().getMethod("takePersistableUriPermission",Uri.class,int.class).invoke(getContentResolver(),uri,1);}catch(Exception ignored){}
   final String name=display(uri);jobs.begin("导入文件",new Jobs.Work(){public void run(Jobs j)throws Exception{j.importFile(uri,request,name);}});
  }else if(request==SAVE_APK||request==SAVE_LOG)jobs.exportTask(new Jobs.Work(){public void run(Jobs j)throws Exception{j.export(uri,request==SAVE_LOG);}});
 }
 void install(){confirmPreviousOutput(false);}
 void installNow(){try{
  if(Build.VERSION.SDK_INT>=26){boolean allowed=(Boolean)getPackageManager().getClass().getMethod("canRequestPackageInstalls").invoke(getPackageManager());
   if(!allowed){startActivity(new Intent("android.settings.MANAGE_UNKNOWN_APP_SOURCES",Uri.parse("package:"+getPackageName())));Toast.makeText(this,"允许此来源后，返回点击安装",Toast.LENGTH_LONG).show();return;}}
  Uri uri=Uri.parse("content://cn.minidayz.patcher.files/latest.apk");Intent i=new Intent(Intent.ACTION_VIEW);i.setDataAndType(uri,"application/vnd.android.package-archive");i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);i.setClipData(ClipData.newRawUri("P版构建结果",uri));startActivity(i);
 }catch(Exception e){Toast.makeText(this,"无法打开安装界面，可先另存 APK 再安装",Toast.LENGTH_LONG).show();}}
}
