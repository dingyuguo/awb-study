#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并 5 份多光谱 AWB 文档为单文件《多光谱AWB研究全集.html》。
方案：主页面 = 侧边目录 + 单个 <iframe>；每份文档完整嵌入 <template>，
iframe 内各自携带原始 CSS 隔离渲染，外观与单份文档完全一致（无全局 CSS 冲突）。"""
import re, os, json

WORK = "/Users/ding/WorkBuddy/AWB研究"

DOCS = [
    ("doc1", "多光谱AWB研究报告.html", "多光谱 AWB 研究综合报告",
     "综合研究入口：研究背景、8 篇核心论文分析、华为专题、技术路线对比、数据集汇总与未来方向。",
     [(r'<div class="section-title"', '</div>', 2), (r'<h3', '</h3>', 3)]),
    ("doc2", "白平衡与光源概念辨析.html", "白平衡与光源概念辨析",
     "把 WB / CCM / 光源 / 白点 / 多光谱 等概念统一到同一框架，厘清四种常见说法的关系。",
     [(r'<h3', '</h3>', 2)]),
    ("doc3", "华为多光谱AWB路线图与论文详解.html", "华为多光谱 AWB 路线图与论文详解",
     "学术轨(IJCV2024 / WACV2025)+ 产业轨(红枫 1.0/2.0)双轨交汇，含方法级论文解读与专利布局。",
     [(r'<h2', '</h2>', 2), (r'<h3', '</h3>', 3)]),
    ("doc4", "LocalAWB研究热点与待解难题.html", "Local AWB 研究热点与待解难题",
     "局部多光源白平衡的原理细节、五条研究主线、现有方案、八大待解难题与未来方向。",
     [(r'<h2', '</h2>', 2), (r'<h3', '</h3>', 3)]),
    ("doc5", "CIC33论文详细讲解.html", "CIC33 论文详细讲解（小白向）",
     "Spectricity CIC33 逐句精讲：领域补习、方法原理、复现指南、实验解读、引用论文分析。",
     [(r'<h2', '</h2>', 2), (r'<h3', '</h3>', 3)]),
]

# 注入到每个文档 <head> 的 CSS：让容器填满 iframe（覆盖原始 max-width 约束）
INJECT_CSS = """
<style id="__awb-override">
/* 全集 iframe 模式：取消固定宽度，内容铺满 */
.container{max-width:100%!important;padding:28px 20px 60px!important;}
body{padding:0!important;}
.hero,.section-title{text-align:left!important;}
pre{max-width:100%!important;overflow-x:auto!important;}
table{max-width:100%!important;display:table!important;}
</style>
"""

# 注入到每个文档 <body> 末尾的脚本：负责 iframe 内滚动高亮 + 响应父页面跳转
INJECT_JS = """
<script>
(function(){
  var map={};document.querySelectorAll('[id]').forEach(function(e){map[e.id]=e;});
  var t=Object.keys(map).map(function(k){return map[k];});
  if(!('IntersectionObserver' in window)||!t.length) return;
  var io=new IntersectionObserver(function(es){
    es.forEach(function(e){ if(e.isIntersecting){ parent.postMessage({__awb:true,id:e.target.id},'*'); } });
  },{rootMargin:'-12% 0px -82% 0px'});
  t.forEach(function(x){ io.observe(x); });
  window.addEventListener('message',function(e){
    if(e.data&&e.data.__goto){ var el=document.getElementById(e.data.__goto); if(el) el.scrollIntoView({behavior:'smooth'}); }
  });
})();
</script>
"""

def read_full(fn):
    return open(os.path.join(WORK, fn), encoding="utf-8").read()

# 1) 抽取每份文档的标题锚点（用于 TOC），并构造嵌入用的完整 HTML（注入滚动脚本）
toc = []          # (docid, doc_title, level, anchor, plain_text)
templates = {}    # docid -> 完整 HTML（含注入脚本）

for docid, fn, title, desc, rules in DOCS:
    html = read_full(fn)
    # ★ 全宽修复：清除所有固定 max-width 约束，让内容铺满 iframe
    # 1) .container 固定宽度 → 全宽
    html = re.sub(r'\.container\s*\{[^}]*max-width\s*:\s*\d+(px|rem|em)[^}]*\}',
                  '.container { width: 100%; max-width: none; padding: 28px 20px 60px; }', html)
    # 2) 其余所有 CSS 规则中的固定 max-width → none 或 100%（排除 media query 和 !important）
    html = re.sub(r'(?<!\n)(?<!\w)(max-width)\s*:\s*(\d+(?:\.\d+)?(px|rem|em|%))(?!\s*!important)',
                  lambda m: f"{m.group(1)}: {'none' if m.group(3) in ('px','rem','em') else '100%'}", html)
    # 3) .hero 居中 → 左对齐
    html = re.sub(r'(\.hero\s*\{[^}]*)text-align\s*:\s*center',
                  r'\1text-align: left', html)
    # 加锚点
    for open_re, close_tag, level in rules:
        close_re = re.escape(close_tag)
        pattern = r'(' + open_re + r'([^>]*)>)' + r'(.*?)' + close_re
        counter = {"n": 0}
        def repl(m, level=level, counter=counter):
            counter["n"] += 1
            open_full = m.group(1)
            inner = m.group(3)
            plain = re.sub(r"<[^>]+>", "", inner).strip()
            plain = re.sub(r"\s+", " ", plain)
            anchor = f"{docid}-h{level}-{counter['n']}"
            toc.append((docid, title, level, anchor, plain))
            new_open = open_full[:-1] + f' id="{anchor}"' + '>'
            return f'{new_open}{inner}{close_tag}'
        html = re.sub(pattern, repl, html, flags=re.S)
    # 注入覆盖 CSS（让容器填满 iframe）+ 滚动脚本
    html = html.replace("</head>", INJECT_CSS + "</head>", 1)
    html = html.replace("</body>", INJECT_JS + "</body>", 1)
    templates[docid] = html

# 2) 生成侧边栏 TOC
toc_html_parts = ['<div class="toc-group"><a href="#" class="toc-link toc-home" data-doc="doc1">⌂ 全集首页</a></div>']
cur_doc = None
for (docid, doc_title, level, anchor, text) in toc:
    if docid != cur_doc:
        cur_doc = docid
        toc_html_parts.append(
            f'<div class="toc-group"><div class="toc-doc" data-doc="{docid}">{doc_title}</div>')
    cls = "toc-link toc-h2" if level == 2 else "toc-link toc-h3"
    toc_html_parts.append(f'<a href="#{anchor}" class="{cls}">{text}</a>')
toc_html = "\n".join(toc_html_parts)

# 3) 主页面 CSS（仅主框架，文档自身样式在 iframe 内隔离）
master_css = """
*{box-sizing:border-box;}
html,body{margin:0;padding:0;height:100%;}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
  background:#070a10;color:#c3ccd8;overflow:hidden;}
.shell{display:flex;height:100vh;}
.sidebar{position:fixed;left:0;top:0;width:280px;height:100vh;overflow-y:auto;
  background:linear-gradient(180deg,#0c1018,#0a0d13);border-right:1px solid rgba(120,140,170,.18);
  padding:22px 0 60px;font-size:13px;z-index:50;}
.sidebar-title{font-size:16px;font-weight:700;color:#e8eef7;padding:0 20px 6px;letter-spacing:.3px;}
.sidebar-sub{font-size:11px;color:#6b7686;padding:0 20px 14px;border-bottom:1px solid rgba(120,140,170,.12);
  margin-bottom:10px;line-height:1.5;}
.toc-group{margin:2px 0 8px;}
.toc-doc{font-size:12.5px;font-weight:700;color:#7fd1c4;padding:10px 20px 5px;cursor:pointer;letter-spacing:.2px;}
.toc-doc:hover{color:#a7e8de;}
.toc-link{display:block;padding:4px 20px;color:#9aa6b6;text-decoration:none;line-height:1.45;
  border-left:2px solid transparent;transition:all .15s;cursor:pointer;}
.toc-link:hover{color:#e8eef7;background:rgba(120,140,170,.08);}
.toc-h2{font-weight:600;color:#c3ccd8;}
.toc-h3{padding-left:34px;font-size:12px;color:#828d9d;}
.toc-home{font-weight:700;color:#e8eef7;background:rgba(63,185,80,.08);border-left:2px solid #3fb950;margin-bottom:4px;}
.toc-link.active{color:#fff;background:rgba(63,185,80,.14);border-left:2px solid #3fb950;}
.content{margin-left:280px;height:100vh;overflow:hidden;background:#0a0d13;}
.viewer{width:100%;height:100%;border:0;display:block;background:#0a0d13;}
.menu-btn{display:none;position:fixed;top:14px;left:14px;z-index:60;background:#1a2030;color:#e8eef7;
  border:1px solid rgba(120,140,170,.3);border-radius:8px;padding:8px 12px;font-size:14px;cursor:pointer;}
@media(max-width:900px){
  .sidebar{transform:translateX(-100%);transition:.25s;width:260px;}
  .sidebar.open{transform:translateX(0);}
  .content{margin-left:0;}
  .menu-btn{display:block;}
}
"""

# 4) 主页面 JS
master_js = """
(function(){
  var viewer=document.getElementById('viewer');
  var DOC={};
  ['doc1','doc2','doc3','doc4','doc5'].forEach(function(id){
    DOC[id]=document.getElementById('tpl-'+id).innerHTML;
  });
  var current=null, pending=null;
  function show(docId, anchor){
    if(current!==docId){
      current=docId; pending=anchor||null;
      viewer.srcdoc=DOC[docId];
    } else if(anchor){
      var d=viewer.contentDocument;
      if(d){ var el=d.getElementById(anchor); if(el) el.scrollIntoView({behavior:'smooth'}); }
    }
  }
  viewer.addEventListener('load',function(){
    if(pending && viewer.contentDocument){
      var el=viewer.contentDocument.getElementById(pending);
      if(el) el.scrollIntoView();
      pending=null;
    }
  });
  document.querySelectorAll('[data-doc]').forEach(function(a){
    a.addEventListener('click',function(ev){ ev.preventDefault(); show(a.getAttribute('data-doc')); });
  });
  document.querySelectorAll('.toc-link[href^="#"]').forEach(function(a){
    a.addEventListener('click',function(ev){
      ev.preventDefault();
      var href=a.getAttribute('href');
      if(href==='#top'){ window.scrollTo({top:0,behavior:'smooth'}); return; }
      var anchor=href.slice(1);
      var docId=anchor.split('-')[0];
      show(docId, anchor);
    });
  });
  window.addEventListener('message',function(e){
    if(e.data&&e.data.__awb){
      document.querySelectorAll('.toc-link').forEach(function(x){ x.classList.remove('active'); });
      var a=document.querySelector('.toc-link[href="#'+e.data.__awb+'"]');
      if(a) a.classList.add('active');
    }
  });
  show('doc1');
})();
"""

# 5) 组装
templates_html = "\n".join(
    f'<template id="tpl-{docid}">{templates[docid]}</template>' for docid, *_ in DOCS)

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>多光谱 AWB 研究全集</title>
<style>
{master_css}
</style>
</head>
<body id="top">
<button class="menu-btn" onclick="document.querySelector('.sidebar').classList.toggle('open')">☰ 目录</button>
<div class="shell">
  <nav class="sidebar">
    <div class="sidebar-title">多光谱 AWB 研究全集</div>
    <div class="sidebar-sub">5 份文档 · 领域综述 / 概念辨析 / 华为路线 / Local AWB / CIC33 精讲</div>
    {toc_html}
  </nav>
  <main class="content">
    <iframe id="viewer" class="viewer" title="文档查看器"></iframe>
  </main>
</div>
{templates_html}
<script>
{master_js}
</script>
</body>
</html>
"""

out = os.path.join(WORK, "多光谱AWB研究全集.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print("WROTE", out, "bytes=", len(html.encode("utf-8")))
print("TOC entries:", len(toc))
for d in set(t[0] for t in toc):
    print(" ", d, sum(1 for t in toc if t[0]==d))
