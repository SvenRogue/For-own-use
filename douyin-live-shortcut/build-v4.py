#!/usr/bin/env python3
# Build a clipboard-first Douyin live-photo Shortcut. No text-entry prompt.
import plistlib, uuid, json
from pathlib import Path

root=Path("douyin-live-shortcut")
actions=[]
def uid(): return str(uuid.uuid4()).upper()
def a(name,**params):
    params.setdefault("UUID",uid())
    actions.append({"WFWorkflowActionIdentifier":"is.workflow.actions."+name,"WFWorkflowActionParameters":params})
    return params["UUID"]
def out(u,name): return {"Type":"ActionOutput","OutputUUID":u,"OutputName":name}
def var(name): return {"Type":"Variable","VariableName":name}
def att(v): return {"WFSerializationType":"WFTextTokenAttachment","Value":v}
def txt(prefix="",ref=None):
    val={"string":prefix+("\uFFFC" if ref is not None else "")}
    if ref is not None: val["attachmentsByRange"]={f"{{{len(prefix)}, 1}}":ref}
    return {"WFSerializationType":"WFTextTokenString","Value":val}
def iff(v,condition,compare):
    group=uid()
    a("conditional",GroupingIdentifier=group,WFControlFlowMode=0,WFCondition=condition,WFConditionalActionString=compare,WFInput={"Type":"Variable","Variable":att(v)})
    return group
def els(group): a("conditional",GroupingIdentifier=group,WFControlFlowMode=1)
def end(group): a("conditional",GroupingIdentifier=group,WFControlFlowMode=2)
def key(v,name): return a("getvalueforkey",WFGetDictionaryValueType="Value",WFDictionaryKey=name,WFInput=att(v))
def notice(title,message): a("alert",WFAlertActionTitle=title,WFAlertActionMessage=message,WFAlertActionCancelButtonShown=False)

a("comment",WFCommentActionText="v4 自动读取剪贴板里的完整抖音分享文案，无需输入或粘贴。公开作品链接发送到 video-bak.mubaiyun.xyz 解析；实况图以 MP4 动态视频（含声音）保存到照片。")
clip=a("getclipboard")
valid=iff(out(clip,"Clipboard"),99,"douyin.com")
matched=a("text.match",WFMatchTextPattern=r"https?://(?:v\.douyin\.com|www\.douyin\.com|m\.douyin\.com|iesdouyin\.com)/[^\s，。！!；;]+",WFMatchTextCaseSensitive=False,text=txt(ref=out(clip,"Clipboard")))
first=a("getitemfromlist",WFInput=att(out(matched,"Matches")),WFItemSpecifier="First Item")
encoded=a("urlencode",WFInput=att(out(first,"Item from List")),WFEncodeMode="Encode")
api=a("downloadurl",WFHTTPMethod="GET",WFURL=txt("https://video-bak.mubaiyun.xyz/api/parse?url=",out(encoded,"URL Encoded Text")))
kind=key(out(api,"Contents of URL"),"mediaType")
live=iff(out(kind,"Dictionary Value"),4,"live_photo")
images=key(out(api,"Contents of URL"),"images")
repeat=uid()
a("repeat.each",GroupingIdentifier=repeat,WFControlFlowMode=0,WFInput=att(out(images,"Dictionary Value")))
mediaurl=key(var("Repeat Item"),"videoUrl")
video=a("downloadurl",WFHTTPMethod="GET",WFURL=txt(ref=out(mediaurl,"Dictionary Value")))
a("savetocameraroll",WFInput=att(out(video,"Contents of URL")))
a("repeat.each",GroupingIdentifier=repeat,WFControlFlowMode=2)
a("notification",WFNotificationActionTitle="实况下载完成",WFNotificationActionBody="请在「照片」查看动态 MP4，保留声音。MP4 不是原生 Live Photo。")
els(live)
notice("未获取实况照片","未解析为 live_photo。可能是普通图集、作品失效、被限制访问或解析接口暂时不可用。")
end(live)
els(valid)
notice("请先复制抖音链接","打开抖音图文作品 → 分享 → 复制链接，然后直接运行本快捷指令；不需要粘贴。")
end(valid)

wf={"WFWorkflowName":"抖音实况下载器 v4","WFWorkflowClientVersion":"3000.0","WFWorkflowClientRelease":"3.0","WFWorkflowMinimumClientVersion":900,
"WFWorkflowMinimumClientVersionString":"900","WFWorkflowIcon":{"WFWorkflowIconStartColor":4271458815,"WFWorkflowIconGlyphNumber":59838},
"WFWorkflowTypes":[],"WFWorkflowInputContentItemClasses":[],"WFWorkflowHasShortcutInputVariables":False,"WFWorkflowActions":actions,"WFWorkflowImportQuestions":[]}
# Validate all conditions, avoiding the missing-comparison crash of v3.
for item in actions:
    n=item["WFWorkflowActionIdentifier"]
    p=item["WFWorkflowActionParameters"]
    if n.endswith(".conditional") and p.get("WFControlFlowMode")==0:
        assert p.get("WFConditionalActionString"), "Empty comparison"
        assert p.get("WFInput",{}).get("Type")=="Variable"
    if n.endswith(".downloadurl"):
        assert p.get("WFURL",{}).get("WFSerializationType")=="WFTextTokenString"
        assert p["WFURL"]["Value"]["attachmentsByRange"]
assert actions[1]["WFWorkflowActionIdentifier"].endswith(".getclipboard")
assert not any(item["WFWorkflowActionIdentifier"].endswith(".ask") for item in actions)
assert sum(x["WFWorkflowActionIdentifier"].endswith(".downloadurl") for x in actions)==2
raw=plistlib.dumps(wf,fmt=plistlib.FMT_XML,sort_keys=False)
(root/"unsigned.xml").write_bytes(raw)
(root/"request.json").write_text(json.dumps({"shortcutName":"抖音实况下载器 v4","shortcut":raw.decode("utf-8")},ensure_ascii=False))
print("v4 output",len(raw),"actions",len(actions),"conditions",2,"downloads",2)
