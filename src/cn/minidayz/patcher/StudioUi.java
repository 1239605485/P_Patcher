package cn.minidayz.patcher;

import android.app.*;
import android.content.*;
import android.graphics.*;
import android.graphics.drawable.*;
import android.view.*;
import android.widget.*;

/** Shared native shell and visual language for installation, AI and settings. */
public final class StudioUi {
 public final Activity a;
 public final boolean dark;
 public final int ink,muted,bg,card,line,accent=0xff168779;
 public LinearLayout body;
 private ScrollView scroll;
 private TextView title,subtitle;
 private Button[] tabs;
 public interface Nav{void select(int tab);}

 public StudioUi(Activity a){
  this.a=a;dark=(a.getResources().getConfiguration().uiMode&0x30)==0x20;
  ink=dark?0xffeef5f4:0xff153831;muted=dark?0xffa7beb9:0xff637d76;
  bg=dark?0xff0f1c1a:0xfff1f5f2;card=dark?0xff192b27:Color.WHITE;line=dark?0xff29433c:0xffe0ebe5;
 }
 public int dp(int n){return (int)(n*a.getResources().getDisplayMetrics().density+.5f);}
 public GradientDrawable shape(int color,int radius){GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(radius));return d;}

 public LinearLayout mount(int selected,final Nav nav){
  LinearLayout frame=new LinearLayout(a);frame.setOrientation(LinearLayout.VERTICAL);frame.setBackgroundColor(bg);
  int statusId=a.getResources().getIdentifier("status_bar_height","dimen","android");
  int bottomId=a.getResources().getIdentifier("navigation_bar_height","dimen","android");
  int top=statusId==0?dp(24):a.getResources().getDimensionPixelSize(statusId);
  int bottom=bottomId==0?dp(16):a.getResources().getDimensionPixelSize(bottomId);
  frame.setPadding(0,top,0,bottom);
  LinearLayout heading=new LinearLayout(a);heading.setOrientation(LinearLayout.VERTICAL);heading.setPadding(dp(20),dp(12),dp(20),dp(8));
  TextView brand=text("P PATCHER  /  补丁助手",11,accent);brand.setTypeface(null,Typeface.BOLD);heading.addView(brand);
  title=text("",25,ink);title.setTypeface(null,Typeface.BOLD);subtitle=text("",12,muted);heading.addView(title);heading.addView(subtitle);frame.addView(heading);
  scroll=new ScrollView(a);scroll.setFillViewport(true);body=new LinearLayout(a);body.setOrientation(LinearLayout.VERTICAL);
  body.setPadding(dp(16),dp(8),dp(16),dp(18));scroll.addView(body);frame.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
  LinearLayout navBar=new LinearLayout(a);navBar.setPadding(dp(10),dp(7),dp(10),dp(5));navBar.setBackgroundColor(card);
  tabs=new Button[4];String[] labels={"安装","AI","诊断","设置"};
  for(int i=0;i<4;i++){
   final int tab=i;Button b=new Button(a);b.setText(labels[i]);b.setTextSize(14);b.setAllCaps(false);
   navBar.addView(b,new LinearLayout.LayoutParams(0,dp(48),1));b.setOnClickListener(new View.OnClickListener(){public void onClick(View v){nav.select(tab);}});tabs[i]=b;
  }
  frame.addView(navBar);a.setContentView(frame);select(selected);return body;
 }
 public void scrollToTop(){if(scroll!=null)scroll.post(new Runnable(){public void run(){scroll.scrollTo(0,0);}});}
 public void select(int i){
  if(i<0||i>=tabs.length)i=0;
  for(int k=0;k<4;k++){tabs[k].setTextColor(k==i?Color.WHITE:muted);tabs[k].setBackgroundDrawable(shape(k==i?accent:card,12));}
  title.setText(new String[]{"安装游戏插件","AI 适配助手","进度与诊断","连接与设置"}[i]);
  Jobs j=Jobs.get(a);subtitle.setText("1.5.0  ·  "+(j.file(1).isFile()?j.apkName:"先选择游戏 APK")+(j.busy?"\n"+j.status+" "+j.progress:""));
 }
 public TextView text(String s,int size,int color){TextView t=new TextView(a);t.setText(s);t.setTextSize(size);t.setTextColor(color);t.setPadding(0,dp(4),0,dp(6));t.setLineSpacing(dp(2),1);return t;}
 public LinearLayout card(LinearLayout parent,String name,String description){
  LinearLayout p=new LinearLayout(a);p.setOrientation(LinearLayout.VERTICAL);p.setPadding(dp(16),dp(14),dp(16),dp(16));p.setBackgroundDrawable(shape(card,18));
  LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.bottomMargin=dp(12);parent.addView(p,lp);
  if(name.length()>0){TextView h=text(name,17,ink);h.setTypeface(null,Typeface.BOLD);p.addView(h);}
  if(description.length()>0)p.addView(text(description,12,muted));return p;
 }
 public void paintButton(Button b,boolean primary){b.setTextColor(primary?Color.WHITE:ink);b.setTextSize(14);b.setAllCaps(false);b.setBackgroundDrawable(shape(primary?accent:line,11));b.setMinHeight(dp(48));}
 public Button button(LinearLayout p,String label,boolean primary,View.OnClickListener click){
  Button b=new Button(a);b.setText(label);b.setTextSize(14);b.setAllCaps(false);b.setTextColor(primary?Color.WHITE:ink);
  b.setPadding(dp(10),dp(8),dp(10),dp(8));b.setMinHeight(dp(48));b.setBackgroundDrawable(shape(primary?accent:line,11));
  LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.topMargin=dp(6);lp.bottomMargin=dp(4);p.addView(b,lp);if(click!=null)b.setOnClickListener(click);return b;
 }
 public void field(EditText e){e.setTextColor(ink);e.setHintTextColor(muted);e.setTextSize(15);e.setPadding(dp(12),dp(12),dp(12),dp(12));e.setBackgroundDrawable(shape(bg,10));LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.topMargin=dp(6);lp.bottomMargin=dp(8);e.setLayoutParams(lp);}
 public static void open(Activity a,int tab){Class<?> target=tab==0||tab==2?MainActivity.class:AiActivity.class;Intent i=new Intent(a,target);i.putExtra("studio_tab",tab);i.addFlags(Intent.FLAG_ACTIVITY_REORDER_TO_FRONT);a.startActivity(i);}
}
