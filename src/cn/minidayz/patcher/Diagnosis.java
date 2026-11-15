package cn.minidayz.patcher;
import org.json.*;
public final class Diagnosis {
 public static JSONObject explain(String code)throws Exception{String action;String kind="manual-input";boolean retry=false;
  if(code.equals("E_INPUT_MISSING")){kind="missing-input";action="请先选择游戏 APK；检查兼容性或生成时还需要插件包，生成时还需原签名文件。按页面提示补齐后重试。";}
  else if(code.equals("E_LOG_INSTALLER_DIAGNOSTIC")){kind="wrong-diagnostic-source";action="这是补丁助手自己的诊断包。若要分析游戏运行错误，请导入游戏内导出的诊断 ZIP 或包含崩溃信息的日志。";}
  else if(code.equals("E_UNSUPPORTED_VERSION")){kind="adaptation-required";action="已自动尝试整包识别和逐文件核对。差异报告列出真实变化；需要适合这些变化的新模块包，改版本号不能修复。";}
  else if(code.startsWith("E_LOCAL_")||code.startsWith("E_RULE_")){kind="local-assistance";action="本地诊断记录已保留。请检查版本证据、插件兼容性与实测规则，必要时转AI分析；不会强行修改未知版本。";}
  else if(code.startsWith("E_AI_")){kind="ai-assistance";action="本次 AI 修改未提交或请求未完成。请检查具体提示、API 设置及目标文本；原插件可继续使用，底层问题请导出分析报告交人工处理。";}
  else if(code.equals("E_STORAGE_LOW")){kind="device-resource";action="助手已清理未完成任务缓存。请释放空间后点击自动处理；已成功生成的 APK 不会被删除。";retry=true;}
  else if(code.equals("E_INTERRUPTED")){kind="recoverable";action="已自动清除中断任务的临时文件，输入和上次成功结果保留。可直接重新自动处理。";retry=true;}
  else if(code.equals("E_MODULE_SIGNATURE")||code.startsWith("E_PAYLOAD")||code.equals("E_MODULE_SIGNER")){kind="module-integrity";action="模块损坏或签名不符，请重新选择完整可信的模块 ZIP；助手不会跳过校验。";}
  else if(code.startsWith("E_KEY")||code.equals("E_INSTALLED_SIGNER")){kind="signing-identity";action="请导入原 P 版签名文件。已安装游戏签名不同需要核对来源，助手不会自动卸载游戏或清除存档。";}
  else if(code.startsWith("E_ZIP")||code.equals("E_NOT_APK")||code.equals("E_DELTA_EOF")){kind="input-integrity";action="请重新选择完整 APK 或模块 ZIP，检查文件是否下载完整；拆分 APK 不能作为完整游戏安装包。";}
  else if(code.equals("E_CANCELLED")){kind="cancelled";action="已清理未完成任务；原输入和上次成功结果保留。可重新自动处理。";retry=true;}
  else if(code.equals("E_RELEASE_TEXT")||code.equals("E_VERSION_CODE")){action="请检查输出名称和版本输入；名称和版本最多 80 个字符，不能换行，内部代码有上限。";}
  else if(code.equals("E_FOREGROUND")){kind="android-service";action="请保持助手在前台并检查系统后台限制后重试。";retry=true;}
  else{kind="diagnostic-required";action="已保留本次失败原因和上次成功结果。请导出诊断，避免反复应用同一个失败补丁。";}
  return new JSONObject().put("category",kind).put("action",action).put("retry_after_action",retry);
 }
}
