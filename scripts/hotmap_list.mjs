// Hot Map bước 1: Top Free theo nước × category -> data/hotmap/top_free.json
// Chạy hằng ngày trong daily_tracking.py (market.py đọc file này).
// Chạy: node scripts/hotmap_list.mjs
import gplay from 'google-play-scraper';
import fs from 'node:fs';

const COUNTRIES = ['us','br','in','id','mx','de','jp','vn'];
const CATS = ['TOOLS','PERSONALIZATION','ART_AND_DESIGN','ENTERTAINMENT','LIFESTYLE','PHOTOGRAPHY','MUSIC_AND_AUDIO','GAME_CASUAL','VIDEO_PLAYERS','PRODUCTIVITY'];
const out = [];
for (const country of COUNTRIES) for (const cat of CATS) {
  try {
    const r = await gplay.list({collection: gplay.collection.TOP_FREE, category: gplay.category[cat], country, num: 200});
    r.forEach((a, i) => out.push({country, cat, rank: i + 1, appId: a.appId, title: a.title, developer: a.developer}));
    console.log(country, cat, r.length);
  } catch (e) { console.log(country, cat, 'ERR', e.message.slice(0, 80)); }
}
const dir = (process.env.DATA_DIR || 'data') + '/hotmap';  // DATA_DIR: chạy test không ghi đè data thật
fs.mkdirSync(dir, {recursive: true});
fs.writeFileSync(dir + '/top_free.json', JSON.stringify(out));
console.log('rows', out.length, 'unique', new Set(out.map(o => o.appId)).size);
