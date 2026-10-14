#!/usr/bin/env python3
"""Build clipboard-only Douyin Live MP4 downloader (v5).

Avoid fragile comparisons on dynamic JSON dictionary values. Conditions are
existence-only; generated plist is statically validated before signing.
"""
import plistlib
import re
import json
import uuid
from pathlib import Path

ROOT = Path("douyin-live-shortcut")
A = []
def uid(): return str(uuid.uuid4()).upper()
def output(action_uuid, name): return {"Type": "ActionOutput", "OutputUUID": action_uuid, "OutputName": name}
def token(v): return {"WFSerializationType": "WFTextTokenAttachment", "Value": v}
def text_token(prefix="", ref=None):
    text = {"string": prefix + ("\uFFFC" if ref is not None else "")}
    if ref is not None:
        text["attachmentsByRange"] = {"{%d, 1}" % len(prefix): ref}
    return {"WFSerializationType": "WFTextTokenString", "Value": text}
def action(name, **parameters):
    parameters.setdefault("UUID", uid())
    A.append({"WFWorkflowActionIdentifier": "is.workflow.actions." + name,
              "WFWorkflowActionParameters": parameters})
    return parameters["UUID"]
def exists(ref):
    group = uid()
    action("conditional", WFControlFlowMode=0, GroupingIdentifier=group,
           WFCondition=100, WFInput={"Type":"Variable", "Variable":token(ref)})
    return group
def otherwise(group):
    action("conditional", WFControlFlowMode=1, GroupingIdentifier=group)
def end_if(group):
    action("conditional", WFControlFlowMode=2, GroupingIdentifier=group)
def field(ref, field_name):
    return action("getvalueforkey", WFInput=token(ref),
                  WFGetDictionaryValueType="Value", WFDictionaryKey=field_name)
def alert(title, message):
    action("alert", WFAlertActionTitle=title, WFAlertActionMessage=message,
           WFAlertActionCancelButtonShown=False)
def download(url_token):
    return action("downloadurl", WFHTTPMethod="GET", WFURL=url_token)

action("comment", WFCommentActionText=(
    "v5：运行时直接读取剪贴板，无需输入框。将公开抖音分享链接发送至"
    "video-bak.mubaiyun.xyz，获取图文实况对应的 MP4 并保存到照片。"
    "普通图片没有动态数据，会自动跳过；MP4 不是苹果原生 Live Photo。"
))
clipboard=action("getclipboard")
matches=action("text.match",
               WFMatchTextPattern=r"https?://(?:v\.douyin\.com|www\.douyin\.com|m\.douyin\.com|iesdouyin\.com)/[^\s，。！!；;]+",
               WFMatchTextCaseSensitive=False,
               text=text_token(ref=output(clipboard, "Clipboard")))
has_link=exists(output(matches,"Matches"))
first=action("getitemfromlist",WFInput=token(output(matches,"Matches")),
             WFItemSpecifier="First Item")
# Douyin short links contain no query parameters: a nested http(s) link is
# valid as the final value of ?url= without an extra "URL Encode" action.
api=download(text_token("https://video-bak.mubaiyun.xyz/api/parse?url=",
                        output(first,"Item from List")))
images=field(output(api, "Contents of URL"),"images")
has_images=exists(output(images, "Dictionary Value"))
loop_group=uid()
loop=action("repeat.each",WFControlFlowMode=0,GroupingIdentifier=loop_group,
            WFInput=token(output(images, "Dictionary Value")))
# "Repeat Item" is the native magic variable scoped to Repeat with Each.
video_url=field({"Type":"Variable","VariableName":"Repeat Item"},"videoUrl")
has_video=exists(output(video_url,"Dictionary Value"))
video_file=download(text_token(ref=output(video_url,"Dictionary Value")))
action("savetocameraroll",WFInput=token(output(video_file,"Contents of URL")))
end_if(has_video)
action("repeat.each",WFControlFlowMode=2,GroupingIdentifier=loop_group)
action("notification",
       WFNotificationActionTitle="抖音图文处理完成",
       WFNotificationActionBody="请检查「照片」中的新视频。无新增视频说明接口未返回实况 MP4。")
otherwise(has_images)
alert("无法取得图文数据","请确认作品是公开的抖音图文实况。若链接正确，可能是解析服务暂时失败。")
end_if(has_images)
otherwise(has_link)
alert("请先复制抖音分享链接","在抖音作品中选择「分享 → 复制链接」，然后直接运行本快捷指令。")
end_if(has_link)

workflow={
    "WFWorkflowName":"抖音实况下载器 v5",
    "WFWorkflowClientVersion":"3000.0",
    "WFWorkflowClientRelease":"3.0",
    "WFWorkflowMinimumClientVersion":900,
    "WFWorkflowIcon":{"WFWorkflowIconStartColor":4271458815,
                      "WFWorkflowIconGlyphNumber":59838},
    "WFWorkflowTypes":[],
    "WFWorkflowInputContentItemClasses":[],
    "WFWorkflowHasShortcutInputVariables":False,
    "WFWorkflowActions":A,
    "WFWorkflowImportQuestions":[],
}
# Check routing, completeness and unsupported interactive input.
assert len(A)>=20
assert A[1]["WFWorkflowActionIdentifier"]=="is.workflow.actions.getclipboard"
assert len([a for a in A if a["WFWorkflowActionIdentifier"].endswith(".downloadurl")])==2
assert len([a for a in A if a["WFWorkflowActionIdentifier"].endswith(".conditional") and
            a["WFWorkflowActionParameters"].get("WFControlFlowMode")==0])==3
assert not any(x["WFWorkflowActionIdentifier"].endswith(".ask")
               or x["WFWorkflowActionIdentifier"].endswith(".choosefrommenu") for x in A)
ids={x["WFWorkflowActionParameters"]["UUID"] for x in A}
for x in A:
    p=x["WFWorkflowActionParameters"]
    if x["WFWorkflowActionIdentifier"].endswith(".conditional") and p.get("WFControlFlowMode")==0:
        assert p["WFCondition"]==100, "No comparison conditions permitted"
        assert p["WFInput"]["Variable"]["WFSerializationType"]=="WFTextTokenAttachment"
        assert not any(k in p for k in ("WFConditionalActionString","WFNumberValue"))
    if x["WFWorkflowActionIdentifier"].endswith(".downloadurl"):
        spec=p["WFURL"]
        assert spec["WFSerializationType"]=="WFTextTokenString"
        ref=list(spec["Value"]["attachmentsByRange"].values())[0]
        assert ref.get("Type")=="ActionOutput" and ref["OutputUUID"] in ids
serialized=plistlib.dumps(workflow, fmt=plistlib.FMT_XML, sort_keys=False)
assert plistlib.loads(serialized)["WFWorkflowActions"]==A
ROOT.joinpath("unsigned.xml").write_bytes(serialized)
ROOT.joinpath("request.json").write_text(json.dumps({
    "shortcutName":"抖音实况下载器 v5",
    "shortcut":serialized.decode("utf-8")
}, ensure_ascii=False))
print("v5 build passed:",len(A),"actions, 3 existence guards, 2 URL downloads, direct clipboard")
