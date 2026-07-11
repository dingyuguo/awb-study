#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并 5 份多光谱 AWB 研究文档为带总目录(侧边栏)的单文件 HTML。
按每份文档实际标题结构分别配置 TOC 抽取规则。"""
import re, os

WORK = "/Users/ding/WorkBuddy/AWB研究"

# (doc_id, 文件名, 文档标题, 简介, 标题规则)
# 标题规则: [(open_tag_start, close_tag, level), ...]  level=2 主章 / level=3 子节
# open_tag_start 不含结尾 '>'，例如 '<div class="section-title"' 或 '<h3'
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

def read_body_css(fn):
    txt = open(os.path.join(WORK, fn), encoding="utf-8").read()
    style = re.search(r"<style>(.*?)</style>", txt, re.S).group(1)
    body = re.search(r"<body>(.*?)</body>", txt, re.S).group(1)
    return style, body

# 1) 合并 CSS（去重保序，主报告放最前保证最完整）
all_css_lines = []
for docid, fn, *_ in DOCS:
    style, _ = read_body_css(fn)
    for ln in style.splitlines():
        all_css_lines.append(ln)
seen, css = set(), []
for ln in all_css_lines:
    s = ln.strip()
    if s and s not in seen:
        seen.add(s); css.append(ln)
css_text = "\n".join(css)

# 2) 逐文档处理：加锚点 + 收集 TOC
toc = []  # (docid, doc_title, level, anchor, text)
sections_html = []

for idx, (docid, fn, title, desc, rules) in enumerate(DOCS, start=1):
    _, body = read_body_css(fn)

    for open_re, close_tag, level in rules:
        close_re = re.escape(close_tag)
        # group1=完整开标签(含class), group2=属性, group3=内部内容
        pattern = r'(' + open_re + r'([^>]*)>)' + r'(.*?)' + close_re
        counter = {"n": 0}
        def repl(m, level=level, counter=counter):
            counter["n"] += 1
            open_full = m.group(1)          # 完整开标签, 如 <div class="section-title">
            inner = m.group(3)
            plain = re.sub(r"<[^>]+>", "", inner).strip()
            plain = re.sub(r"\s+", " ", plain)
            anchor = f"{docid}-h{level}-{counter['n']}"
            toc.append((docid, title, level, anchor, plain))
            # 在开标签的 '>' 前插入 id, 保留原 class 等属性
            new_open = open_full[:-1] + f' id="{anchor}"' + '>'
            return f'{new_open}{inner}{close_tag}'
        body = re.sub(pattern, repl, body, flags=re.S)

    cover = f'''
    <section id="{docid}" class="doc-cover">
      <div class="doc-cover-badge">文档 {idx} / {len(DOCS)}</div>
      <h1 class="doc-cover-title">{title}</h1>
      <p class="doc-cover-desc">{desc}</p>
    </section>
    <hr class="doc-sep"/>
    '''
    sections_html.append(cover + body)

content_inner = "\n".join(sections_html)

# 3) 生成侧边栏 TOC
toc_html_parts = ['<div class="toc-group"><a href="#top" class="toc-link toc-home">⌂ 全集首页</a></div>']
cur_doc = None
for (docid, doc_title, level, anchor, text) in toc:
    if docid != cur_doc:
        cur_doc = docid
        toc_html_parts.append(f'<div class="toc-group"><div class="toc-doc">{doc_title}</div>')
    cls = "toc-link toc-h2" if level == 2 else "toc-link toc-h3"
    toc_html_parts.append(f'<a href="#{anchor}" class="{cls}">{text}</a>')
toc_html = "\n".join(toc_html_parts)

# 4) 布局 CSS
layout_css = """
*{box-sizing:border-box;}
body{margin:0;}
.shell{display:flex;min-height:100vh;}
.sidebar{position:fixed;left:0;top:0;width:320px;height:100vh;overflow-y:auto;
  background:linear-gradient(180deg,#0c1018,#0a0d13);border-right:1px solid rgba(120,140,170,.18);
  padding:22px 0 60px;font-size:13px;z-index:50;}
.sidebar-title{font-size:16px;font-weight:700;color:#e8eef7;padding:0 20px 6px;letter-spacing:.3px;}
.sidebar-sub{font-size:11px;color:#6b7686;padding:0 20px 14px;border-bottom:1px solid rgba(120,140,170,.12);margin-bottom:10px;line-height:1.5;}
.toc-group{margin:2px 0 8px;}
.toc-doc{font-size:12px;font-weight:700;color:#7fd1c4;padding:8px 20px 4px;letter-spacing:.2px;}
.toc-link{display:block;padding:4px 20px;color:#9aa6b6;text-decoration:none;line-height:1.45;
  border-left:2px solid transparent;transition:all .15s;}
.toc-link:hover{color:#e8eef7;background:rgba(120,140,170,.08);}
.toc-h2{font-weight:600;color:#c3ccd8;}
.toc-h3{padding-left:34px;font-size:12px;color:#828d9d;}
.toc-home{font-weight:700;color:#e8eef7;background:rgba(63,185,80,.08);border-left:2px solid #3fb950;}
.toc-link.active{color:#fff;background:rgba(63,185,80,.14);border-left:2px solid #3fb950;}
.content{margin-left:320px;flex:1;min-width:0;}
.doc-cover{padding:56px 48px 28px;}
.doc-cover-badge{display:inline-block;font-size:12px;color:#3fb950;border:1px solid rgba(63,185,80,.4);
  padding:3px 12px;border-radius:20px;margin-bottom:16px;background:rgba(63,185,80,.06);}
.doc-cover-title{font-size:34px;font-weight:800;color:#f2f6fc;margin:0 0 12px;line-height:1.2;}
.doc-cover-desc{font-size:15px;color:#9aa6b6;max-width:780px;line-height:1.7;margin:0;}
.doc-sep{border:none;border-top:1px solid rgba(120,140,170,.15);margin:0 48px;}
.content > section[id^="doc"]{scroll-margin-top:20px;}
.content [id]{scroll-margin-top:16px;}
@media(max-width:900px){
  .sidebar{transform:translateX(-100%);transition:.25s;width:290px;}
  .sidebar.open{transform:translateX(0);}
  .content{margin-left:0;}
  .menu-btn{display:block;}
}
.menu-btn{display:none;position:fixed;top:14px;left:14px;z-index:60;background:#1a2030;color:#e8eef7;
  border:1px solid rgba(120,140,170,.3);border-radius:8px;padding:8px 12px;font-size:14px;cursor:pointer;}
"""

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>多光谱 AWB 研究全集</title>
<style>
{css_text}
{layout_css}
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
    <section id="overview" class="doc-cover">
      <div class="doc-cover-badge">总目录</div>
      <h1 class="doc-cover-title">多光谱 AWB 研究全集</h1>
      <p class="doc-cover-desc">本全集整合了关于<strong>多光谱自动白平衡（AWB）</strong>与<strong>局部 AWB（Local AWB）</strong>的五份研究文档，覆盖：领域综述与前沿论文、WB/CCM/光源/白点的概念辨析、华为从学术研究到红枫落地的完整技术路线、Local AWB 的研究热点与待解难题，以及对 Spectricity CIC33 论文的小白向逐句精讲。点击左侧目录可在各章节间跳转。</p>
    </section>
    <hr class="doc-sep"/>
    {content_inner}
  </main>
</div>
<script>
(function(){{
  var links = Array.prototype.slice.call(document.querySelectorAll('.toc-link[href^="#"]'));
  var map = {{}};
  links.forEach(function(a){{ map[a.getAttribute('href').slice(1)] = a; }});
  var targets = Array.prototype.slice.call(document.querySelectorAll('[id]')).filter(function(el){{ return map[el.id]; }});
  var obs = new IntersectionObserver(function(entries){{
    entries.forEach(function(e){{
      if(e.isIntersecting){{
        links.forEach(function(l){{ l.classList.remove('active'); }});
        var a = map[e.target.id];
        if(a) a.classList.add('active');
      }}
    }});
  }}, {{rootMargin:'-10% 0px -80% 0px', threshold:0}});
  targets.forEach(function(t){{ obs.observe(t); }});
}})();
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
