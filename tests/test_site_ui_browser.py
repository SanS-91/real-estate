"""Cross-site browser audit: compact mobile, tablet and desktop.

Uses the runner's system Chromium; never mutates production data.
Checks visual overflow, navigable Data Status, touch-scrolled tables,
correct article tags and language toggling across all seven pages.
"""
import asyncio
import json
import shutil
from pathlib import Path
from playwright.async_api import async_playwright

BASE="http://127.0.0.1:8765/"
CASES=[
    "index.html",
    "research.html",
    "market.html?view=overview",
    "market.html?view=projects",
    "market.html?view=pricing",
    "market.html?view=news",
    "legal.html?view=overview",
    "legal.html?view=documents",
    "legal.html?view=news",
    "infrastructure.html?view=overview",
    "infrastructure.html?view=projects",
    "infrastructure.html?view=news",
    "macro.html?view=overview",
    "macro.html?view=news",
    "macro.html?view=fx&series=usd-vnd-central-rate",
    "maintenance.html",
]
WIDTHS=[360,390,820,1366]
ARTIFACTS=Path("artifacts/ui-audit")
ARTIFACTS.mkdir(parents=True,exist_ok=True)

async def run():
    executable = next((shutil.which(c) for c in
      ("google-chrome","chromium","chromium-browser") if shutil.which(c)),None)
    assert executable, "System Chromium unavailable"
    failures=[]
    pass_count=0
    async with async_playwright() as playwright:
        browser=await playwright.chromium.launch(
            headless=True, executable_path=executable,
            args=["--no-sandbox","--disable-dev-shm-usage","--disable-gpu"])
        for width in WIDTHS:
            context=await browser.new_context(
                viewport={"width":width,"height":844},
                locale="vi-VN",reduced_motion="reduce")
            for path in CASES:
                page=await context.new_page()
                errors=[]
                page.on("pageerror",lambda error: errors.append(str(error)[:180]))
                try:
                    await page.goto(BASE+path,wait_until="domcontentloaded",timeout=45000)
                    await page.wait_for_timeout(850)
                    measurements=await page.evaluate("""() => ({
                      innerWidth:window.innerWidth,
                      scrollWidth:document.documentElement.scrollWidth,
                      bodyScroll:document.body.scrollWidth,
                      navItems:[...document.querySelectorAll('.main-nav a')].map(x=>x.getAttribute('href')),
                      visibleMain:getComputedStyle(document.querySelector('.main-nav')).display!=='none',
                      mobileMenu:getComputedStyle(document.querySelector('[data-mobile-menu-button]')).display!=='none',
                      activeLink:document.querySelector('.main-nav a.is-active')?.getAttribute('href'),
                      wide:[...document.querySelectorAll('body *')].filter(x=>{
                        const r=x.getBoundingClientRect();
                        return r.width>0 && r.right>window.innerWidth+5 &&
                          getComputedStyle(x).position!=='fixed' &&
                          !x.closest('.table-wrap,.tabs,.market-news-topics');
                      }).slice(0,5).map(x=>x.tagName+'.'+String(x.className).slice(0,70))
                    })""")
                    assert len(measurements["navItems"])==7,(path,measurements["navItems"])
                    assert "maintenance.html" in measurements["navItems"],path
                    # Same explicit tab label in both primary and touch menu;
                    # article/data pages translate their content separately.
                    assert await page.locator(".main-nav a[href='maintenance.html']").text_content()=="Maintenance"
                    assert await page.locator("[data-mobile-nav] a[href='maintenance.html']").text_content()=="Maintenance"
                    expected_mobile=width<1200
                    assert measurements["mobileMenu"]==expected_mobile,(width,path,"menu")
                    assert measurements["visibleMain"]!=expected_mobile,(width,path,"desktop nav")
                    assert measurements["scrollWidth"]<=width+3,(width,path,measurements)
                    if path=="maintenance.html":
                        assert measurements["activeLink"]=="maintenance.html"
                    if path=="index.html":
                        await page.locator(".today-card").first.wait_for(timeout=12000)
                        assert await page.locator(".today-card").count()==4,(width,"four modules")
                        assert await page.locator(".metric-card").count()<=4,(width,"home macro must remain concise")
                        assert await page.locator(".home-more-history").get_attribute("open") is None
                        for card in await page.locator(".today-card").all():
                            items=card.locator(".compact-list li")
                            count=await items.count()
                            assert count<=3,(width,count)
                            if count and await items.first.locator(".compact-link").count():
                                for item in await items.all():
                                    assert await item.locator("time").count()==1,(width,"source dated item")
                                    assert (await item.locator("time").inner_text()).strip(),(width,"empty update date")
                        assert await page.locator("body .home-snapshot, body .demo-banner").count()==0
                        for card in await page.locator(".metric-card").all():
                            assert await card.locator(".metric-card__footer").count()==1
                        assert await page.locator(".home-header-actions [data-search-open]").count()==1
                    if path=="index.html":
                        menu=page.locator("[data-mobile-menu-button]")
                        if expected_mobile:
                            await menu.click()
                            assert await menu.get_attribute("aria-expanded")=="true"
                            assert await page.locator("[data-mobile-nav] a[href='maintenance.html']").count()==1
                            await page.keyboard.press("Escape")
                            assert await menu.get_attribute("aria-expanded")=="false"
                    if path=="infrastructure.html?view=overview":
                        table=page.locator(".data-table--infra tbody tr")
                        await table.first.wait_for(timeout=12000)
                        assert await table.count()==8,(width,"eight infrastructure records")
                        assert await page.locator(".infra-milestone-grid .infra-milestone").count()>=3
                    if path=="macro.html?view=overview":
                        await page.locator(".macro-metric-card").first.wait_for(timeout=12000)
                        assert await page.locator(".macro-metric-card .macro-cadence").count()>=4
                        assert await page.locator(".macro-overview-cadence-note").count()==1
                        release=page.locator(".macro-release-list .macro-release-row")
                        assert await release.count()>=3,(width,"latest production release entries")
                        assert "DEMO" not in (await page.locator(".macro-release-list").inner_text())
                    if path in ("market.html?view=news", "legal.html?view=news",
                                "infrastructure.html?view=news", "macro.html?view=news"):
                        module=path.split(".html")[0]
                        section=page.locator(".market-news")
                        await section.wait_for(timeout=12000)
                        assert await section.locator(".market-news-filters").count()==1
                        assert await section.locator(".market-news-topics").count()==1
                        assert await section.locator("[data-news-source]").count()==1
                        assert await section.locator("[data-news-days]").count()==1
                        heading=section.locator(f'[data-news-view-label="{module}.title"]')
                        await heading.wait_for(timeout=12000)
                        vietnamese={"market":"Tin tức thị trường", "legal":"Tin tức pháp lý",
                                    "infrastructure":"Tin tức hạ tầng","macro":"Tin tức vĩ mô"}
                        assert await heading.text_content()==vietnamese[module]
                        cards=section.locator(".market-news-card")
                        assert await cards.count()>0,(width,module,"no sourced news cards")
                        toggle=page.locator("[data-language-toggle]")
                        await toggle.click()
                        english={"market":"Real estate market news", "legal":"Legal news",
                                 "infrastructure":"Infrastructure news","macro":"Macro news"}
                        assert await heading.text_content()==english[module],(module,"English heading")
                        await toggle.click()
                        assert await heading.text_content()==vietnamese[module],(module,"Vietnamese heading restore")
                    if path=="market.html?view=pricing":
                        audit=page.locator("[data-market-history-audit]")
                        await audit.wait_for(timeout=12000)
                        assert await audit.count()==1,(width,"one opt-in pricing history matrix")
                        assert await audit.get_attribute("open") is None,(width,"history must start folded")
                        await audit.locator("summary").click()
                        assert await audit.get_attribute("open") is not None
                        rows=audit.locator(".data-table--history-readiness tbody tr")
                        assert await rows.count()==13,(width,"all 13 projects have history coverage")
                        grand=rows.filter(has=page.locator('[data-project-id="vinhomes-grand-park"]')).first
                        assert await grand.count()==1,(width,"Grand Park pricing-history entry")
                        grand_text=await grand.inner_text()
                        assert "Lumière Boulevard: 2 tháng" in grand_text,(width,"Sep and Oct subproject continuity",grand_text)
                        assert "1 chỉ mục" in grand_text and "1 đã kiểm chứng" in grand_text,(width,"provenance labels",grand_text)
                        assert await rows.first.locator("[data-project-id]").count()==1
                        text=(await audit.inner_text()).lower()
                        assert "không phải kết luận xu hướng" in text
                        assert "số tháng của các phân khu không được cộng" in text
                        peer=page.locator("[data-market-peer-monthly]")
                        await peer.wait_for(timeout=12000)
                        assert await peer.count()==1,(width,"peer comparable source panel")
                        assert await peer.get_attribute("open") is None
                        await peer.locator("summary").click()
                        assert await peer.get_attribute("open") is not None
                        peer_rows=peer.locator(".data-table--peer-monthly tbody tr")
                        assert await peer_rows.count()==3,(width,"exactly three named peer sources")
                        peer_names=await peer_rows.all_inner_texts()
                        for name in ("Masteri Thảo Điền","Estella Heights","The Panorama"):
                            assert any(name in label for label in peer_names),(width,name,"peer missing")
                        assert "không phải ASP giao dịch" in (await peer.inner_text())
                        await peer.locator("summary").click()
                        assert await peer.get_attribute("open") is None
                        # A collapsed audit must not crowd mobile page before opening.
                        await audit.locator("summary").click()
                        assert await audit.get_attribute("open") is None
                    if path in ("market.html?view=overview","market.html?view=projects"):
                        table=page.locator(".data-table--market-projects")
                        await table.wait_for(timeout=12000)
                        total=await table.locator("tbody tr").count()
                        assert total==(8 if "overview" in path else 13),(width,path,total)
                        asks=table.locator(".market-asking-range")
                        assert await asks.count()==total,(width,path,"price range markers")
                        trend=table.locator(".market-trend")
                        assert await trend.count()==total,(width,path,"trend markers")
                        for kind in ("up","down"):
                            marker=table.locator(f".market-trend--{kind}").first
                            if await marker.count():
                                color=await marker.evaluate("el=>getComputedStyle(el).color")
                                assert color!= "rgb(102, 112, 133)",(path,kind,"trend not colored")
                        up=table.locator(".market-trend--up")
                        if await up.count():
                            assert "↑" in (await up.first.text_content()),(path,"up arrow")
                        down=table.locator(".market-trend--down")
                        if await down.count():
                            assert "↓" in (await down.first.text_content()),(path,"down arrow")
                    if path=="market.html?view=news":
                        await page.locator("[data-news-topic='pricing']").first.wait_for(timeout=12000)
                        pills=page.locator(".market-news-card__topic")
                        if await pills.count():
                            first=pills.first
                            assert await first.get_attribute("data-topic") in {
                               "pricing","supply","sales","projects","legal","infrastructure","research"}
                            # Topic tags need an actual visual distinction on
                            # both cards and filters, not just source HTML labels.
                            style=await first.evaluate("""el=>{
                              const c=getComputedStyle(el);
                              return {color:c.color, bg:c.backgroundColor, border:c.borderColor};
                            }""")
                            assert style["bg"] not in ("rgba(0, 0, 0, 0)","rgb(255, 255, 255)"),(path,style)
                            await first.click()
                            assert "news-topic=" in page.url,(width,"clickable tags do not filter",page.url)
                    if path in ("legal.html?view=overview", "legal.html?view=documents",
                                "infrastructure.html?view=overview", "infrastructure.html?view=projects"):
                        table = page.locator(".mobile-record-table").first
                        await table.wait_for(timeout=12000)
                        expected_rows = page.locator(".mobile-record-table tbody tr")
                        assert await expected_rows.count() >= 1, (path, "empty record table")
                        layout = await table.evaluate("""el => {
                            const row = el.querySelector('tbody tr');
                            const title = row.querySelector('button.table-link');
                            return {
                                display: getComputedStyle(el).display,
                                width: el.getBoundingClientRect().width,
                                scrollWidth: el.scrollWidth,
                                clientWidth: el.clientWidth,
                                rowDisplay: getComputedStyle(row).display,
                                rowWidth: row.getBoundingClientRect().width,
                                titleWidth: title?.closest('td')?.getBoundingClientRect().width ?? 0,
                                fields: [...row.querySelectorAll('td:not(.table-empty)')].map(
                                    td => ({vi: td.dataset.labelVi, en: td.dataset.labelEn}))
                            };
                        }""")
                        assert len(layout["fields"])==7, (path,layout)
                        assert all(f["vi"] and f["en"] for f in layout["fields"]), (path,layout)
                        if width<=767:
                            assert layout["display"]=="block" and layout["rowDisplay"]=="grid", (width,path,layout)
                            assert layout["scrollWidth"]<=layout["clientWidth"]+2, (width,path,layout)
                            assert layout["rowWidth"]<=width-20, (width,path,layout)
                            assert layout["titleWidth"]>=layout["rowWidth"]-48, (width,path,layout)
                            label_td=page.locator(".mobile-record-table tbody tr:first-child td:nth-child(1)" if "legal." in path
                                                else ".mobile-record-table tbody tr:first-child td:nth-child(2)")
                            def before_value():
                                return label_td.evaluate("(el) => getComputedStyle(el,'::before').content")
                            assert "Số hiệu" in (await before_value()) if "legal." in path else "Loại" in (await before_value())
                            await page.locator("[data-language-toggle]").click()
                            assert "Number" in (await before_value()) if "legal." in path else "Type" in (await before_value())
                            await page.locator("[data-language-toggle]").click()
                        else:
                            assert layout["display"]=="table", (width,path,layout)
                        if width==390:
                            await page.locator(".mobile-record-table button.table-link").first.click()
                            await page.locator("[data-drawer-overlay].is-open").wait_for(timeout=6000)
                            await page.locator("[data-drawer-close]").click()
                    # Mobile data list cards (not comparison matrices).
                    mobile_lists = {
                        "market.html?view=projects": ("market-projects", 9),
                        "macro.html?view=overview": ("macro", 5),
                        "macro.html?view=fx&series=usd-vnd-central-rate": ("macro-history", 5),
                        "maintenance.html": ("maintenance", 7),
                    }
                    if path in mobile_lists:
                        family, count = mobile_lists[path]
                        selector = ("[data-maintenance-table] .data-table--maintenance.mobile-record-table"
                                    if family=="maintenance" else f".data-table--{family}.mobile-record-table")
                        table = page.locator(selector).first
                        await table.wait_for(timeout=14000)
                        layout = await table.evaluate("""el => {
                          const row = el.querySelector('tbody tr');
                          const cells = [...row.querySelectorAll('td')];
                          const title = row.querySelector('td:first-child');
                          return {
                            display: getComputedStyle(el).display,
                            rowDisplay: getComputedStyle(row).display,
                            tableWidth: el.clientWidth,
                            scrollWidth: el.scrollWidth,
                            rowWidth: row.getBoundingClientRect().width,
                            cells: cells.map(td=>[td.dataset.labelVi,td.dataset.labelEn]),
                            firstWidth: title?.getBoundingClientRect().width??0
                          };
                        }""")
                        assert len(layout["cells"])==count,(path,layout)
                        assert all(vi and en for vi,en in layout["cells"]),(path,layout)
                        if width<=767:
                            assert layout["display"]=="block" and layout["rowDisplay"]=="grid",(width,path,layout)
                            assert layout["scrollWidth"]<=layout["tableWidth"]+3,(width,path,layout)
                            assert layout["rowWidth"]<=width-20,(width,path,layout)
                            if family in ("market-projects","macro"):
                                assert layout["firstWidth"]>=layout["rowWidth"]-48,(width,path,layout)
                            label_td=table.locator("tbody tr:first-child td:nth-child(3)" if family=="maintenance" else "tbody tr:first-child td").first
                            before=lambda: label_td.evaluate("(el)=>getComputedStyle(el,'::before').content")
                            vi_label=await before()
                            await page.locator("[data-language-toggle]").click()
                            en_label=await before()
                            assert vi_label!=en_label,(width,path,vi_label,en_label)
                            await page.locator("[data-language-toggle]").click()
                        else:
                            assert layout["display"]=="table",(width,path,layout)
                        if width==390 and family in ("market-projects","macro"):
                            await table.locator("button.table-link").first.click()
                            await page.locator("[data-drawer-overlay].is-open").wait_for(timeout=6500)
                            await page.locator("[data-drawer-close]").click()
                    if width==390 and path=="maintenance.html":
                        tables=page.locator(".table-wrap")
                        if await tables.count():
                            await tables.first.evaluate(
                              "(el)=>{if(el.scrollWidth>el.clientWidth)el.scrollLeft=90;}")
                    pass_count+=1
                except Exception as e:
                    failures.append({"width":width,"path":path,"error":str(e),"js_errors":errors[:3]})
                    try:
                        safe=path.split('?')[0].replace('.html','')
                        await page.screenshot(path=str(ARTIFACTS/f"{safe}-{width}.png"),full_page=True,timeout=12000)
                    except Exception:
                        pass
                finally:
                    await page.close()
            await context.close()
        await browser.close()
    print(json.dumps({"cases":len(CASES)*len(WIDTHS),"passed":pass_count,
        "failures":failures},ensure_ascii=False,indent=2))
    assert not failures,"UI viewport regression failures — see above diagnostics and screenshots"

if __name__=="__main__":
    asyncio.run(run())
