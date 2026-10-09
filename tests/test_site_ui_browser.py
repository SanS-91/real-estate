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
                        menu=page.locator("[data-mobile-menu-button]")
                        if expected_mobile:
                            await menu.click()
                            assert await menu.get_attribute("aria-expanded")=="true"
                            assert await page.locator("[data-mobile-nav] a[href='maintenance.html']").count()==1
                            await page.keyboard.press("Escape")
                            assert await menu.get_attribute("aria-expanded")=="false"
                    if path in ("legal.html?view=news", "infrastructure.html?view=news",
                                "macro.html?view=news"):
                        section=path.split(".html")[0]
                        heading=page.locator(f'[data-news-view-label="{section}.title"]')
                        await heading.wait_for(timeout=12000)
                        vietnamese={
                            "legal":"Tin tức & phân tích pháp lý",
                            "infrastructure":"Tin tức & tiến độ hạ tầng",
                            "macro":"Tin tức & nghiên cứu vĩ mô (minh họa)"
                        }
                        assert await heading.text_content()==vietnamese[section],(path,"Vietnamese title")
                        chips=page.locator(".article-row__meta .news-kind-chip")
                        if await chips.count():
                            chip=chips.first
                            assert await chip.get_attribute("data-news-kind"),(path,"source taxonomy")
                            assert "-" not in (await chip.text_content()),(path,"raw technical label")
                        toggle=page.locator("[data-language-toggle]")
                        await toggle.click()
                        expected={"legal":"Legal news & analysis",
                                  "infrastructure":"Infrastructure news & milestones",
                                  "macro":"Illustrative macro news & research"}
                        assert await heading.text_content()==expected[section],(path,"English toggle")
                        await toggle.click()
                        assert await heading.text_content()==vietnamese[section],(path,"Vietnamese toggle restore")
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
