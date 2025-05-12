// MCP Crawler Server (JSON-RPC, CommonJS)
const http = require('http');
const Parser = require('rss-parser');
const fetch = require('node-fetch');
const cheerio = require('cheerio');
const fs = require('fs');
const parser = new Parser();

// 支援多個 RSS 來源
const RSS_SOURCES = [
    // Google News
    q => `https://news.google.com/rss/search?q=${encodeURIComponent(q)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant`,
    // Yahoo 奇摩新聞
    q => `https://tw.news.yahoo.com/rss/search?p=${encodeURIComponent(q)}`,
    // 商業周刊
    _ => 'https://www.businessweekly.com.tw/rss',
    // 聯合新聞網
    _ => 'https://udn.com/rssfeed/news/2/6638?ch=news',
    // 中央社
    _ => 'https://www.cna.com.tw/rss.aspx'
];

// 取得新聞全文（簡易版，僅抓取 <p> 文字）
async function fetchFullText(url) {
    try {
        const res = await fetch(url, { timeout: 5000 });
        const html = await res.text();
        const $ = cheerio.load(html);
        // 取所有 <p> 文字
        return $('p').map((i, el) => $(el).text()).get().join('\n');
    } catch (e) {
        return '';
    }
}

async function crawl_news(params) {
    const { query, start_date, end_date, fulltext = false, only_urls = false } = params;
    let allNews = [];
    for (const getRss of RSS_SOURCES) {
        try {
            const feed = await parser.parseURL(getRss(query));
            for (const item of feed.items) {
                // 過濾日期
                const pubDate = item.pubDate ? new Date(item.pubDate) : null;
                if (pubDate) {
                    const start = new Date(start_date);
                    const end = new Date(end_date);
                    if (pubDate < start || pubDate > end) continue;
                }
                allNews.push({
                    query,
                    title: item.title,
                    url: item.link,
                    content: item.contentSnippet || '',
                    source: feed.title || '',
                    crawl_date: pubDate ? pubDate.toISOString().slice(0, 10) : '',
                });
            }
        } catch (e) { /* 忽略單一來源錯誤 */ }
    }
    // 去除重複網址
    allNews = allNews.filter((v, i, a) => a.findIndex(t => t.url === v.url) === i);

    // 只要網址清單
    if (only_urls) {
        const urls = allNews.map(n => n.url);
        fs.writeFileSync('news_urls.txt', urls.join('\n'), 'utf8');
        return urls;
    }

    // 需要全文
    if (fulltext) {
        for (const news of allNews) {
            news.fulltext = await fetchFullText(news.url);
        }
        fs.writeFileSync('news_fulltext.json', JSON.stringify(allNews, null, 2), 'utf8');
    }

    // 也可在這裡呼叫 AI 摘要 API，將摘要寫入 news.ai_summary

    return allNews;
}

const server = http.createServer((req, res) => {
    if (req.method === 'POST') {
        let body = '';
        req.on('data', chunk => { body += chunk; });
        req.on('end', async () => {
            try {
                const rpc = JSON.parse(body);
                if (rpc.method === 'crawl_perplexity') {
                    const result = await crawl_news(rpc.params);
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ jsonrpc: '2.0', result, id: rpc.id }));
                } else {
                    res.writeHead(404);
                    res.end();
                }
            } catch (e) {
                res.writeHead(500);
                res.end(JSON.stringify({ error: e.toString() }));
            }
        });
    } else {
        res.writeHead(200);
        res.end('MCP Crawler Server is running.');
    }
});

const PORT = 3000;
server.listen(PORT, () => {
    console.log(`MCP Crawler Server running at http://localhost:${PORT}/`);
});
