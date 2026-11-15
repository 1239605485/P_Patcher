package cn.minidayz.patcher;
import org.json.*;
/** Identify current task status separately from retained historical failure and game logs. */
public final class DiagnosticHandoff {
 public static String render(JSONObject snapshot,boolean priorFailure,boolean gameLog){
  String status=snapshot.optString("status","unknown"),stage=snapshot.optString("stage",""),err=snapshot.optString("error","");
  StringBuilder text=new StringBuilder("P版补丁助手诊断（非游戏运行日志）\n当前助手任务状态：").append(status).append("\n当前任务阶段：").append(stage);
  if("failed".equals(status)||"cancelled".equals(status)||"interrupted".equals(status))text.append("\n当前任务错误：").append(err);
  else text.append("\n当前助手任务没有记录失败；此状态不能证明游戏安装或运行成功。");
  text.append("\n输入校验：").append(snapshot.optString("input_sha256")).append("\n适配档案：").append(snapshot.optString("profile_id"));
  if(priorFailure)text.append("\nlast_failure.json 是保留的最近一次历史失败，不一定属于当前任务；请核对时间与输入。");
  text.append(gameLog?"\n诊断包附带用户导入的游戏日志；日志内容及归属仍需核验。":"\n没有附带已导入的游戏运行日志；无法从此包判断游戏是否闪退或为何闪退。");
  text.append("\n如需排查游戏运行，请提供游戏内导出的诊断日志；无法进入游戏时提供系统崩溃信息和复现步骤。\n");
  return text.toString();
 }
}
