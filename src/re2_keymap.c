#include <windows.h>
#include <stdint.h>
#include <stdarg.h>
#include "atlas.h"
#include "bilingual_assets.h"
#include "items.h"
#include "overlay_data.h"
#include "overlay_icons.h"
#include "fill_masks.h"
#include "rank_glyphs.h"
#include "monsters.h"
#define MONSTER_KIND 50 /* overlay icon kind of monster category 0 */
typedef struct { unsigned char pl,floor; short x,y; unsigned char seen,unlock,key,scenario_mask,bank; } Door;
#include "doors-all.h"
typedef RoomLabel_EN RoomLabel;
typedef RoomName_EN RoomName;
typedef ItemLabel_EN ItemLabel;
static unsigned char *game;
static HANDLE logfile=INVALID_HANDLE_VALUE;
static void log_line(const char *fmt,...){if(logfile==INVALID_HANDLE_VALUE)return;char out[512];va_list ap;va_start(ap,fmt);int n=wvsprintfA(out,fmt,ap);va_end(ap);DWORD wrote;if(n>0&&n<512)WriteFile(logfile,out,(DWORD)n,&wrote,NULL);}
static int equal(const void *a,const void *b,unsigned n){const unsigned char*x=a,*y=b;for(unsigned i=0;i<n;i++)if(x[i]!=y[i])return 0;return 1;}
static unsigned frames;
static int overlay_enabled=1,room_names_enabled=1,locks_enabled=0,items_enabled=0,documents_enabled=0,puzzles_enabled=0;
static int english_enabled=1,monsters_enabled=0,common_enabled=0;
static unsigned scope=1; /* [8] 1 visited rooms, 2 + rooms revealed by the floor map, 3 all rooms */
static unsigned name_opacity=70,name_size=100;
static int rank_enabled;
static unsigned size_value(int value){if(value<50)value=50;if(value>150)value=150;return (unsigned)(value+5)/10*10;}
static int name_dimension(unsigned pixels){return (pixels*name_size+200)/400;}
static int drawing_names;
static unsigned opacity_value(int value){if(value<10)value=10;if(value>100)value=100;return (unsigned)(value+5)/10*10;}
static unsigned toggle_was_down;
static char settings_path[MAX_PATH];
static void save_settings(void){
 if(!settings_path[0])return;
 char value[4]={'0',0};
 const char *keys[]={"All","Rooms","Locks","Items","Documents","Puzzles","English","Enemies","CommonItems"};
 int values[]={overlay_enabled,room_names_enabled,locks_enabled,items_enabled,documents_enabled,puzzles_enabled,english_enabled,monsters_enabled,common_enabled};
 for(unsigned i=0;i<9;i++){value[0]=values[i]?'1':'0';WritePrivateProfileStringA("MapOverlay",keys[i],value,settings_path);}
 value[0]=(char)('0'+scope);WritePrivateProfileStringA("MapOverlay","Scope",value,settings_path);
 wsprintfA(value,"%u",name_size);WritePrivateProfileStringA("MapOverlay","NameSize",value,settings_path);
 wsprintfA(value,"%u",name_opacity);WritePrivateProfileStringA("MapOverlay","NameOpacity",value,settings_path);
 value[0]=rank_enabled?'1':'0';WritePrivateProfileStringA("MapOverlay","Rank",value,settings_path);
}
static void load_settings(void){
 overlay_enabled=GetPrivateProfileIntA("MapOverlay","All",1,settings_path)!=0;
 room_names_enabled=GetPrivateProfileIntA("MapOverlay","Rooms",1,settings_path)!=0;
 locks_enabled=GetPrivateProfileIntA("MapOverlay","Locks",0,settings_path)!=0;
 items_enabled=GetPrivateProfileIntA("MapOverlay","Items",0,settings_path)!=0;
 documents_enabled=GetPrivateProfileIntA("MapOverlay","Documents",0,settings_path)!=0;
 puzzles_enabled=GetPrivateProfileIntA("MapOverlay","Puzzles",0,settings_path)!=0;
 english_enabled=GetPrivateProfileIntA("MapOverlay","English",1,settings_path)!=0;
 monsters_enabled=GetPrivateProfileIntA("MapOverlay","Enemies",0,settings_path)!=0;
 common_enabled=GetPrivateProfileIntA("MapOverlay","CommonItems",0,settings_path)!=0;
 name_size=size_value((int)GetPrivateProfileIntA("MapOverlay","NameSize",100,settings_path));
 rank_enabled=GetPrivateProfileIntA("MapOverlay","Rank",0,settings_path)!=0;
 name_opacity=opacity_value((int)GetPrivateProfileIntA("MapOverlay","NameOpacity",70,settings_path));
 scope=GetPrivateProfileIntA("MapOverlay","Scope",1,settings_path);if(scope<1||scope>3)scope=1;
}

static void update_toggle(unsigned mode,int down){
 unsigned pressed=(unsigned)down&~toggle_was_down;
 if(mode==0){
  if(pressed&1)overlay_enabled=!overlay_enabled;
  if(pressed&2)room_names_enabled=!room_names_enabled;
  if(pressed&4)locks_enabled=!locks_enabled;
  if(pressed&8)items_enabled=!items_enabled;
  if(pressed&16)documents_enabled=!documents_enabled;
  if(pressed&32)english_enabled=!english_enabled;
  if(pressed&64)puzzles_enabled=!puzzles_enabled;
  if(pressed&128)common_enabled=!common_enabled;
  if(pressed&256)monsters_enabled=!monsters_enabled;
  if(pressed&4096)scope=scope%3+1;
  if(down&2048){
   if(pressed&512&&name_opacity<100)name_opacity+=10;
   if(pressed&1024&&name_opacity>10)name_opacity-=10;
  }else{
   if(pressed&512&&name_size<150)name_size+=10;
   if(pressed&1024&&name_size>50)name_size-=10;
  }
  if(pressed&6143)save_settings();
 }
 toggle_was_down=(unsigned)down;
}

static void (__cdecl *map_draw)(void);
static int (__cdecl *flat_rect)(void*,int,int);
static int (__cdecl *check_bit)(void*,unsigned);
static uintptr_t addr(unsigned va){return (uintptr_t)game+va-0x400000;}
static unsigned texture,room_textures_ko[ROOM_LABEL_PAGE_COUNT_KO],room_textures_en[ROOM_LABEL_PAGE_COUNT_EN];
static unsigned item_textures_ko[ITEM_LABEL_PAGE_COUNT_KO],item_textures_en[ITEM_LABEL_PAGE_COUNT_EN],icon_texture;
static unsigned fill_textures[FILL_MASK_FLOORS],rank_texture;
static unsigned nav_texture,quad_color; // area arrows (nav_arrows_draw): packet colour word, 0 = untinted
static uintptr_t texture_device;
static int test_texture;
static const RoomLabel *active_room_labels(void){return english_enabled?room_labels_EN:(const RoomLabel*)room_labels_KO;}
static const RoomName *active_room_names(void){return english_enabled?room_names_EN:(const RoomName*)room_names_KO;}
static unsigned active_room_count(void){return english_enabled?sizeof(room_names_EN)/sizeof(room_names_EN[0]):sizeof(room_names_KO)/sizeof(room_names_KO[0]);}
static unsigned active_help_start(void){return english_enabled?ROOM_HELP_LABEL_EN:ROOM_HELP_LABEL_KO;}
static const unsigned short *active_room_pixels(unsigned p){return english_enabled?room_label_pixels_EN[p]:room_label_pixels_KO[p];}
static unsigned *active_room_cache(unsigned p){return english_enabled?room_textures_en+p:room_textures_ko+p;}
static const ItemLabel *active_item_labels(void){return english_enabled?item_labels_EN:(const ItemLabel*)item_labels_KO;}
static unsigned active_item_count(void){return english_enabled?ITEM_LABEL_COUNT_EN:ITEM_LABEL_COUNT_KO;}
static const unsigned short *active_item_pixels(unsigned p){return english_enabled?item_label_pixels_EN[p]:item_label_pixels_KO[p];}
static unsigned *active_item_cache(unsigned p){return english_enabled?item_textures_en+p:item_textures_ko+p;}
static unsigned create_texture(const unsigned short *pixels){
 unsigned char *marni=*(unsigned char**)addr(0x6805b8);
 if(!marni)return 0;
 unsigned char desc[64]={0};
 *(uintptr_t*)desc=addr(0x5173fc);*(uintptr_t*)(desc+4)=(uintptr_t)pixels;
 desc[0xe]=0;desc[0xf]=31;desc[0x10]=5;desc[0x11]=5;
 desc[0x12]=31;desc[0x13]=5;desc[0x14]=10;desc[0x15]=31;desc[0x16]=5;
 *(short*)(desc+0x1a)=256;*(short*)(desc+0x1c)=256;*(short*)(desc+0x1e)=512;
 desc[0x24]=16;desc[0x26]=1;desc[0x27]=1;desc[0x29]=1;desc[0x2a]=1;
 unsigned (__thiscall *create)(void*,void*,unsigned)=(void*)addr(0x405ec0);
 return create(marni,desc,0x12);
}
static int resident_english;
static unsigned cached_texture(unsigned *cache,const unsigned short *pixels){
 if(test_texture)return texture;
 unsigned char *marni=*(unsigned char**)addr(0x6805b8);
 if(!marni)return 0;
 uintptr_t device=*(uintptr_t*)(marni+0x8c8338);
 if(!device)return 0;
 if(texture_device!=device){
  texture=0;for(unsigned i=0;i<ROOM_LABEL_PAGE_COUNT_KO;i++)room_textures_ko[i]=0;
  for(unsigned i=0;i<ROOM_LABEL_PAGE_COUNT_EN;i++)room_textures_en[i]=0;
  for(unsigned i=0;i<ITEM_LABEL_PAGE_COUNT_KO;i++)item_textures_ko[i]=0;
  for(unsigned i=0;i<ITEM_LABEL_PAGE_COUNT_EN;i++)item_textures_en[i]=0;
  icon_texture=rank_texture=nav_texture=0;for(unsigned i=0;i<FILL_MASK_FLOORS;i++)fill_textures[i]=0;
  texture_device=device;resident_english=english_enabled;
 }
 if(resident_english!=english_enabled){
  // Native handle/work pools (0x416c40/0x416b50) are shared with the game and ran dry after ~68 handles with both
  // languages resident, leaving English legend row 2 (pages 10-11) blank (user 2026-10-26). Keep one language only.
  void (__thiscall *release)(void*,unsigned)=(void*)addr(0x416be0);
  unsigned *rooms=resident_english?room_textures_en:room_textures_ko,*items=resident_english?item_textures_en:item_textures_ko;
  unsigned nr=resident_english?ROOM_LABEL_PAGE_COUNT_EN:ROOM_LABEL_PAGE_COUNT_KO,ni=resident_english?ITEM_LABEL_PAGE_COUNT_EN:ITEM_LABEL_PAGE_COUNT_KO;
  for(unsigned i=0;i<nr;i++)if(rooms[i]){release(marni,rooms[i]);rooms[i]=0;}
  for(unsigned i=0;i<ni;i++)if(items[i]){release(marni,items[i]);items[i]=0;}
  resident_english=english_enabled;
 }
 if(!*cache){*cache=create_texture(pixels);if(*cache||frames%120==1)log_line("atlas texture=%u device=%08lx\n",*cache,(unsigned long)device);}
 return *cache;
}
static unsigned get_texture(void){return cached_texture(&texture,atlas_pixels);}
typedef struct {short x,y,w,h;} Bounds;
static Bounds occupied[512]; // police 1F draws ~200 quads; a full list keeps label placement exact
static unsigned occupied_count;
static void reserve(int x,int y,int w,int h){if(occupied_count<sizeof(occupied)/sizeof(occupied[0]))occupied[occupied_count++]=(Bounds){x,y,w,h};}
static void quad_draw(int x,int y,int w,int h,unsigned u,unsigned v,unsigned sw,unsigned sh,unsigned tex){
 uintptr_t next=*(uintptr_t*)addr(0x524e1c),end=*(uintptr_t*)addr(0x524e20);
 if(!tex||w<1||h<1||w>317||h>237||next>end||end-next<32+8192)return;
 if(x<1)x=1;if(x+w>318)x=318-w;
 if(y<1)y=1;if(y+h>238)y=238-h;
 unsigned char *p=(unsigned char*)next;
 for(unsigned j=0;j<32;j++)p[j]=0;
 *(unsigned*)(p+4)=0x24;*(unsigned*)(p+8)=tex;
 if(quad_color){*(unsigned*)(p+4)=0x400025;*(unsigned*)(p+28)=quad_color;}
 else if(drawing_names&&name_opacity<100){
  // Native coloured-texture packet: alpha in byte31; SRCALPHA/INVSRCALPHA, RGB555 texture unchanged.
  *(unsigned*)(p+4)=0x400025;*(unsigned*)(p+28)=((name_opacity*255+50)/100<<24)|0x808080;
 }
 *(short*)(p+16)=x;*(short*)(p+18)=y;
 *(short*)(p+20)=x+w-1;*(short*)(p+22)=y+h-1;
 p[24]=u;p[25]=v;p[26]=u+sw-1;p[27]=v+sh-1;
 void (__thiscall *queue)(void*,void*,unsigned)=(void*)addr(0x4021c0);
 // Native key-marker priority keeps additions underneath map transition fades.
 queue(*(void**)addr(0x6805b8),p,6);
 *(uintptr_t*)addr(0x524e1c)=next+32;
 reserve(x,y,w,h);
}
// Lock icons share one visible size: atlas rects are cropped to their art, longest side 7.5 px (user 2026-10-27:
// the Lockpick looked larger than the suit keys when every rect was stretched to 12 px wide).
#define LOCK_ICON_TENTHS 75
static void icon_box(int px,int py,const Icon *i,int *x,int *y,int *w,int *h){
 int m=i->w>i->h?i->w:i->h;
 *w=(i->w*LOCK_ICON_TENTHS+m*5)/(m*10);*h=(i->h*LOCK_ICON_TENTHS+m*5)/(m*10);
 if(*w<1)*w=1;if(*h<1)*h=1;
 *x=px-*w/2;*y=py-*h/2;
 if(*x<1)*x=1;if(*x+*w>318)*x=318-*w;
 if(*y<1)*y=1;if(*y+*h>238)*y=238-*h;
}
// High-priority boxes (key stars, key names, puzzle diamonds) are occupied[0..high_count). Names are translucent and
// the renderer puts translucent packets under every opaque one, so queue order cannot let a name cover an icon:
// lower-priority icons overlapping these boxes are not drawn instead (user 2026-10-26).
static unsigned high_count;
static int under_high(int x,int y,int w,int h){
 for(unsigned j=0;j<high_count;j++){
  const Bounds *r=occupied+j;
  if(x<r->x+r->w&&r->x<x+w&&y<r->y+r->h&&r->y<y+h)return 1;
 }
 return 0;
}
// Same, ignoring the marker an area-map badge is attached to: a star/diamond-sized high box (<= 8 px; names are
// larger and still block) containing the point (cx,cy).
#define MAP_BADGE 3
static int under_high_except(int x,int y,int w,int h,int cx,int cy){
 for(unsigned j=0;j<high_count;j++){
  const Bounds *r=occupied+j;
  if(r->w<=8&&r->h<=8&&r->x<=cx&&cx<r->x+r->w&&r->y<=cy&&cy<r->y+r->h)continue;
  if(x<r->x+r->w&&r->x<x+w&&y<r->y+r->h&&r->y<y+h)return 1;
 }
 return 0;
}
// Least-overlap placement among the given candidates around (px,py), drawn at w x h.
// Overlap weights while key names choose a spot: occupied[0..hard_count) (key stars, puzzle diamonds, legend) 8x,
// [room_lo..room_hi) room names 4x, anything else (locks/files/markers, hidden on overlap) 1x.
static unsigned hard_count,room_lo,room_hi;
static void place_at(int px,int py,int w,int h,unsigned u,unsigned v,unsigned sw,unsigned sh,unsigned tex,
                     const short (*offsets)[2],unsigned n){
 int bx=1,by=1,best=0x7fffffff;
 for(unsigned c=0;c<n;c++){
  int x=px-w/2+offsets[c][0],y=py-h/2+offsets[c][1],score=0;
  if(x<1)x=1;if(x+w>318)x=318-w;
  if(y<1)y=1;if(y+h>238)y=238-h;
  for(unsigned j=0;j<occupied_count;j++){
   Bounds *r=occupied+j;
   int l=x>r->x?x:r->x,t=y>r->y?y:r->y;
   int right=x+w<r->x+r->w?x+w:r->x+r->w,bottom=y+h<r->y+r->h?y+h:r->y+r->h;
   if(right>l&&bottom>t)score+=(right-l)*(bottom-t)*(j<hard_count?8:j>=room_lo&&j<room_hi?4:1);
  }
  if(score<best){best=score;bx=x;by=y;}if(!score)break;
 }
 quad_draw(bx,by,w,h,u,v,sw,sh,tex);
}
// Key-item names always touch their marker box (mx,my,ms): right, left, below, above, then below/above running right
// or left from the marker edge. No gap and no far candidates (user 2026-10-26: must stay near).
static void item_label_draw(int mx,int my,int ms,int w,int h,unsigned u,unsigned v,unsigned sw,unsigned sh,unsigned tex){
 int px=mx+ms/2,py=my+ms/2,bx=px-w/2,by=py-h/2,cy=my+ms/2-h/2-by,cx=mx+ms/2-w/2-bx;
 const short offsets[8][2]={{(short)(mx+ms-bx),(short)cy},{(short)(mx-w-bx),(short)cy},{(short)cx,(short)(my+ms-by)},
  {(short)cx,(short)(my-h-by)},{(short)(mx-bx),(short)(my+ms-by)},{(short)(mx+ms-w-bx),(short)(my+ms-by)},
  {(short)(mx-bx),(short)(my-h-by)},{(short)(mx+ms-w-bx),(short)(my-h-by)}};
 drawing_names=1;place_at(px,py,w,h,u,v,sw,sh,tex,offsets,8);drawing_names=0;
}
// Room names stay exactly centred on the native room sprite; no collision displacement.
static void room_label_draw(int px,int py,unsigned u,unsigned v,unsigned sw,unsigned sh,unsigned tex){
 int w=(sw+ROOM_LABEL_SCALE_KO/2)/ROOM_LABEL_SCALE_KO,h=(sh+ROOM_LABEL_SCALE_KO/2)/ROOM_LABEL_SCALE_KO;
 quad_draw(px-w/2,py-h/2,w,h,u,v,sw,sh,tex);
}
// Live rank estimate, same formula as the native result screen 0x4b6e10..0x4b7099:
// time 100 (<=2.5h, -10 per started hour after, 10 steps max) + saves (<=19: 100-5n) + sprays (<=5: 100-15n),
// -50 (floor 0) after an infinite weapon set fg_status 0x800000 (0x502890); A>=269 B>=199 C>=144 D>=99 else E.
static unsigned rank_score(unsigned secs,unsigned saves,unsigned sprays,unsigned flags,unsigned *rank){
 unsigned steps=0,edge=9000;
 while(secs>edge&&steps<10){edge+=3600;steps++;}
 unsigned score=100-10*steps+(saves<=19?100-5*saves:0)+(sprays<=5?100-15*sprays:0);
 if(flags&0x800000)score=score>49?score-50:0;
 static const unsigned short limits[]={269,199,144,99};
 unsigned r=0;while(r<4&&score<limits[r])r++;
 *rank=r;return score;
}
static int glyph_dry; // measure only (rank line centring)
static int glyph_put(int x,int y,unsigned id,unsigned tex){
 const RankGlyph *g=rank_glyphs+id;int w=(g->w+2)/4,h=(g->h+2)/4;
 if(!glyph_dry)quad_draw(x,y+(5-h)/2,w,h,g->u,g->v,g->w,g->h,tex);return x+w;
}
static int number_put(int x,int y,unsigned n,unsigned digits,unsigned tex){
 char d[10];unsigned k=0;do{d[k++]=n%10;n/=10;}while(n||k<digits);
 while(k)x=glyph_put(x,y,d[--k],tex);return x;
}
// Hidden in Easy (0x4000000) and bonus modes (0x2000000, time-only rank).
static int rank_line(int x,int y,unsigned tex,unsigned flags){
 unsigned secs=*(uint32_t*)addr(0x680588),saves=*(unsigned short*)addr(0x98e9bc),sprays=*(unsigned short*)addr(0x98e9ba);
 if(saves==0xffff)saves=0; // new-game sentinel (0x4b770b)
 unsigned rank,score=rank_score(secs,saves,sprays,flags,&rank);
 unsigned w=english_enabled?RANK_WORD_EN:RANK_WORD_KO;
 x=glyph_put(x,y,w,tex)+2;x=glyph_put(x,y,11+rank,tex)+2;x=number_put(x,y,score,1,tex);x=glyph_put(x,y,w+1,tex)+4;
 x=number_put(x,y,secs/3600,1,tex);x=glyph_put(x,y,10,tex);x=number_put(x,y,secs/60%60,2,tex);x=glyph_put(x,y,10,tex);
 x=number_put(x,y,secs%60,2,tex)+4;
 x=glyph_put(x,y,w+2,tex)+1;x=number_put(x,y,saves,1,tex)+4;x=glyph_put(x,y,w+3,tex)+1;x=number_put(x,y,sprays,1,tex);
 if(flags&0x800000)x=glyph_put(x+4,y,w+4,tex);
 return x;
}
// Right-aligned above the native compass (x250,y21,w32,h48).
#define RANK_Y 8
static unsigned marker_pl(unsigned pl);
static void rank_draw(void){
 unsigned flags=*(uint32_t*)addr(0x989ed0);
 if(!rank_enabled||flags&0x6000000||marker_pl(0)>1)return; // easy/bonus, Extreme Battle, 4th Survivor
 unsigned tex=cached_texture(&rank_texture,rank_glyph_pixels);if(!tex)return;
 glyph_dry=1;int w=rank_line(0,RANK_Y,tex,flags);glyph_dry=0;
 int x=318-w;
 rank_line(x,RANK_Y,tex,flags);
}
static unsigned fill_texture(unsigned floor);
// Text-only legend; room and key-item name controls share the existing settings.
#define LEGEND_ROWS 13
#define LEGEND_COLUMNS 6
// [8] display scope. Revealed = the native map's own test for an unvisited room (0x4fae39..0x4faea9): the floor's
// map bit in bank 0x98ec1c (byte +5 of the Leon 0x53eaf8 / Claire 0x53eb98 floor-table entry, set when the floor
// map is taken) and the room entry's visibility mask (+0xe, or +0xf when 0x989ef8 bit 0 is set): bit 0 = only in
// scenario B, bit 1 = only in scenario A; both set = never drawn before a visit (e.g. Sewer save room, junction).
static int room_shown(unsigned pl,unsigned floor,unsigned seen){
 if(scope>=3||check_bit((void*)addr(0x98ec04),seen))return 1;
 if(scope<2||floor>=20)return 0;
 const unsigned char *f=(const unsigned char*)addr(pl?0x53eb98:0x53eaf8)+floor*8;
 if(!check_bit((void*)addr(0x98ec1c),f[5]))return 0;
 const unsigned char *e=(const unsigned char*)addr(*(const uint32_t*)f);
 unsigned b=(*(uint32_t*)addr(0x989ed0)&0x40000000)!=0,alt=*(unsigned char*)addr(0x989ef8)&1;
 for(unsigned k=0;k<f[4];k++,e+=16){
  unsigned m=e[alt?0xf:0xe];
  if(e[0xc]==seen&&!(m&1&&!b)&&!(m&2&&b))return 1;
 }
 return 0;
}
static int common_item(unsigned item){
 return item==20||item==21||item==22||item==24||item==25||item==26||item==27||item==29||item==30||item==35||item==38||item==39||item==40;
}
static int map_item(unsigned item){return item>=200&&item<=205;}
// [3] key items, [6] common pickups, [4] area maps (with documents), as in the RE1 HD Remaster map mod.
static int item_enabled(unsigned item){return map_item(item)?documents_enabled:common_item(item)?common_enabled:items_enabled;}
#define LEGEND_Y 210
static void help_draw(void){
 const unsigned state[10]={overlay_enabled?1:2,room_names_enabled?3:4,locks_enabled?5:6,
                          items_enabled?7:8,documents_enabled?9:10,puzzles_enabled?11:12,
                          common_enabled?17:18,monsters_enabled?15:16,18+scope,english_enabled?14:13};
 const unsigned scale=english_enabled?ROOM_LABEL_SCALE_EN:ROOM_LABEL_SCALE_KO;
 const unsigned columns=english_enabled?5:6;
 const RoomLabel *base=active_room_labels()+active_help_start(),*title=base;
 unsigned title_w=(title->w+scale/2)/scale;
 unsigned col_width[LEGEND_COLUMNS]={0};
 for(unsigned n=0;n<10;n++){
  unsigned order_col=n%5,col=english_enabled?order_col:(order_col<3?order_col:order_col+1);
  const RoomLabel*l=base+state[n];unsigned w=(l->w+scale/2)/scale;
  if(w>col_width[col])col_width[col]=w;
 }
 if(!english_enabled)col_width[3]=48; // reserve the arrow lane in Korean's empty fourth column
 int x[LEGEND_COLUMNS]={8};
 for(unsigned col=1;col<columns;col++){
  unsigned gap=4+(english_enabled&&col==3?24:0);
  x[col]=x[col-1]+(int)col_width[col-1]+(int)gap;
 }
 unsigned title_h=(title->h+scale/2)/scale;
 unsigned t=cached_texture(active_room_cache(title->page),active_room_pixels(title->page));
 unsigned legend_y=LEGEND_Y;
 if(t)room_label_draw(x[0]+title_w/2,legend_y+title_h/2,title->u,title->v,title->w,title->h,t);
 unsigned cursor=x[0]+title_w+6;
 for(unsigned n=0;n<2;n++){
  unsigned id=n?32+(name_size-50)/10:22+(name_opacity-10)/10;
  const RoomLabel*l=base+id;unsigned w=(l->w+scale/2)/scale;
  unsigned tex=cached_texture(active_room_cache(l->page),active_room_pixels(l->page));
  if(tex)room_label_draw(cursor+w/2,legend_y+title_h/2,l->u,l->v,l->w,l->h,tex);
  cursor+=w+6;
 }
 for(unsigned n=0;n<10;n++){
  unsigned row,col;
  row=n/5;unsigned order_col=n%5;col=english_enabled?order_col:(order_col<3?order_col:order_col+1);
  const RoomLabel*l=base+state[n];unsigned w=(l->w+scale/2)/scale,h=(l->h+scale/2)/scale;
  unsigned tex=cached_texture(active_room_cache(l->page),active_room_pixels(l->page));
  if(tex)room_label_draw(x[col]+w/2,legend_y+10+row*8+h/2,l->u,l->v,l->w,l->h,tex);
 }
 rank_draw();
}
__declspec(dllexport) unsigned __cdecl KeyMapTestRank(unsigned secs,unsigned saves,unsigned sprays,unsigned flags){
 unsigned rank,score=rank_score(secs,saves,sprays,flags,&rank);return score|rank<<16;
}
static int bank_bit(unsigned bank,unsigned bit){
 if(bank==130||bank==131)return *(short*)addr(0x98eae4+(bank-100)*2)==(short)bit; // switch on SCD var 0x1e/0x1f
 if(bank>34)return 0;
 uintptr_t p=*(uintptr_t*)addr(0x53b218+bank*4);
 return p&&check_bit((void*)p,bit)!=0; // native checker returns the raw mask, not 0/1
}
// Extreme Battle loads ROOMA..G instead of ROOM1..7 (0x98e798=9): its rows are tagged pl|2. 4th Survivor/Tofu
// (bank0 bits 28/31) has no pickups, locks or saves: tag 4 matches no row. Arrange (bank0 bit 25) is a row guard.
static unsigned marker_pl(unsigned pl){
 if(bank_bit(0,28)||bank_bit(0,31))return 4;
 return bank_bit(0,7)?pl|2:pl;
}
// [7] monsters (extract_monsters.py): icon kind MONSTER_KIND+category (12 species, kinds 50..61); hidden once the spawn's global id is dead in
// bank 6 (stage < 3, not bonus) or bank 7 (0x4e77d0). 4th Survivor keeps its monsters (real player key, not tag 4).
static unsigned monster_pl(unsigned pl){unsigned m=marker_pl(pl);return m==4?pl:m;}
static int monster_dead(const MapMonster *m){
 if(m->gid==255)return 0;
 return bank_bit(m->dbank==6&&!(*(uint32_t*)addr(0x989ed0)&0x2000000)?6:7,m->gid);
}
static int guards_pass(const MapItemGuard *g,unsigned n){
 for(unsigned k=0;k<n;k++)if(bank_bit(g[k].bank,g[k].bit)!=g[k].value)return 0;
 return 1;
}
// A drawn puzzle diamond within 5 px of a key item: draw the combined sprite (kind 15, cyan star inside a larger
// amber diamond) over that diamond so both stay distinguishable (user 2026-10-22).
#define STAR_NEAR 5
#define PUZZLE_KEY_W 6 /* 80% of the previous 7 px combined marker */
static const MapInteraction *puzzle_near(unsigned pl,unsigned mpl,unsigned floor,int x,int y){
 if(!overlay_enabled||!puzzles_enabled)return 0;
 for(unsigned j=0;j<sizeof(map_interactions)/sizeof(map_interactions[0]);j++){
  const MapInteraction *m=map_interactions+j;
  if(m->pl==mpl&&m->floor==floor&&m->kind==6&&m->x-x<=STAR_NEAR&&x-m->x<=STAR_NEAR&&m->y-y<=STAR_NEAR&&y-m->y<=STAR_NEAR&&
     room_shown(pl,floor,m->seen)&&guards_pass(interaction_guards+m->guard_start,m->guard_count))return m;
 }
 return 0;
}
// Key items sitting on a drawn puzzle (puzzle_near), collected once per frame: their marker becomes the combined
// sprite and that puzzle's plain diamond is not drawn at all. The native queue draws earlier quads over later ones,
// so draw order alone left a 6 px diamond on top of the combined marker (user 2026-10-23).
#define COMBO_MAX 32
static const MapItem *combo_item[COMBO_MAX];
static const MapInteraction *combo_puzzle[COMBO_MAX];
static unsigned combo_count;
static void collect_combos(unsigned pl,unsigned mpl,unsigned floor){
 combo_count=0;
 if(!overlay_enabled||!items_enabled)return;
 for(unsigned j=0;j<sizeof(map_items)/sizeof(map_items[0])&&combo_count<COMBO_MAX;j++){
  const MapItem *i=map_items+j;
  if(i->pl!=mpl||i->floor!=floor||map_item(i->item)||common_item(i->item)||!room_shown(pl,floor,i->seen)||
     bank_bit(i->bank,i->bit)||!guards_pass(map_item_guards+i->guard_start,i->guard_count))continue;
  const MapInteraction *m=puzzle_near(pl,mpl,floor,i->x,i->y);
  if(m){combo_item[combo_count]=i;combo_puzzle[combo_count++]=m;}
 }
}
static const MapInteraction *combo_of(const MapItem *i){
 for(unsigned k=0;k<combo_count;k++)if(combo_item[k]==i)return combo_puzzle[k];
 return 0;
}
static int puzzle_replaced(const MapInteraction *m){
 for(unsigned k=0;k<combo_count;k++)if(combo_puzzle[k]==m)return 1;
 return 0;
}
// Any pickup in this visited room whose own pickup bit is clear and whose guards pass.
static int room_pending(unsigned pl,unsigned floor,unsigned seen){
 for(unsigned j=0;j<sizeof(room_pickups)/sizeof(room_pickups[0]);j++){
  const RoomPickup *p=room_pickups+j;
  if(p->pl==pl&&p->floor==floor&&p->seen==seen&&!bank_bit(p->bank,p->bit)&&guards_pass(room_pickup_guards+p->guard_start,p->guard_count))return 1;
 }
 return 0;
}
// Native room fill call 0x4faf3f -> 0x440280(sprite,0x20,10,0): CLUT row 0/2 visited (blue), +1 = current room (red).
// Pending rooms: native fill unchanged, then the same sprite again in additive blend ([sprite]=1 -> 0x524e24[1]=0x200000,
// Marni SRCALPHA/ONE); its packet is retextured with an orange copy of the floor's room shapes (CLUT index 1 of
// page 0x20, fill_masks.h). Blue + orange stays distinct under protan/deutan/tritan vision (the old red row gave purple).
#define PENDING_RGB555 (0x1c|(0x0f<<5)) /* R=0xe0,G=0x78,B=0: Okabe-Ito orange family */
static unsigned short fill_pages[FILL_MASK_FLOORS][65536]; // kept alive: Marni may re-read source pixels
static unsigned fill_texture(unsigned floor){
 if(floor>=FILL_MASK_FLOORS)return 0;
 unsigned short *page=fill_pages[floor];
 if(!page[0]&&!fill_textures[floor]) // expand once; page[0] is outside every room (u,v>=1)
  for(unsigned i=0;i<65536;i++)page[i]=(fill_masks[floor][i>>3]&(0x80>>(i&7)))?PENDING_RGB555:0;
 return cached_texture(fill_textures+floor,page);
}
#define PROJ_CENTRE 6
uintptr_t fill_entry __asm__("re2_fill_entry"); // room-table entry: caller's ebx at the call
int __cdecl fill_draw(unsigned char *s,unsigned slot,unsigned prio,unsigned mode) __asm__("re2_fill_draw");
void fill_stub(void) __asm__("re2_fill_stub");
__asm__(".text\n.globl re2_fill_stub\nre2_fill_stub:\n movl %ebx, re2_fill_entry\n jmp re2_fill_draw\n");
static int (__cdecl *sprite_draw)(void*,unsigned,unsigned,unsigned);
static unsigned tinted;
int __cdecl fill_draw(unsigned char *s,unsigned slot,unsigned prio,unsigned mode){
 int r=sprite_draw(s,slot,prio,mode);
 if(!overlay_enabled)return r;
 const unsigned char *e=(const unsigned char*)fill_entry;
 if(!r||!e||slot!=0x20||prio!=10||s[7]!=2||(*(unsigned short*)(s+0xe)&1))return r;
 uintptr_t next=*(uintptr_t*)addr(0x524e1c),end=*(uintptr_t*)addr(0x524e20);
 if(next>end||end-next<32+8192)return r; // keep the overlay's label headroom
 if(!room_pending(marker_pl(*(uint32_t*)addr(0x989ed0)>>31),*(unsigned char*)addr(0x691f7a),e[0xc]))return r;
 unsigned floor=*(unsigned char*)addr(0x691f7a),tex=fill_texture(floor);
 if(!tex)return r;
 unsigned char c[0x28];
 for(unsigned i=0;i<sizeof(c);i++)c[i]=s[i];
 *(uint32_t*)c=1;c[4]=c[5]=c[6]=0x80;c[7]=2;*(unsigned short*)(c+0xe)|=1;
 uintptr_t at=*(uintptr_t*)addr(0x524e1c);
 if(sprite_draw(c,slot,prio,mode)&&*(uintptr_t*)addr(0x524e1c)==at+32){
  *(unsigned*)(at+8)=tex;*(unsigned*)(at+12)=0; // own direct-colour texture, no CLUT row
  tinted++;
 }
 return r;
}
// Room names never dodge: the generator placed them inside their room or at the end of a leader line, and runtime
// displacement left names outside rooms with no line (user 2026-10-26). A resized name grows away from its leader end.
static void room_box(const RoomName *r,const RoomLabel *l,int dx,int dy,int *x,int *y,int *w,int *h){
 int cx=r->x,cy=r->y;
 if(r->lx0|r->ly0|r->lx1|r->ly1){cx=r->lx1+(cx-r->lx1)*(int)name_size/100;cy=r->ly1+(cy-r->ly1)*(int)name_size/100;}
 *w=name_dimension(l->w);*h=name_dimension(l->h);*x=cx+dx-*w/2;*y=cy+dy-*h/2;
}
static const Icon *door_icon(const Door *d,unsigned pl,unsigned mpl,unsigned floor,unsigned flags){
 if(d->pl!=mpl||d->floor!=floor)return 0;
 if((d->key==93&&(flags&0x40000000))||
    ((d->key==94||d->key==95||d->key==98||d->key==99)&&!(flags&0x40000000)))return 0;
 if(!(flags&0x40000000)){if(d->scenario_mask&64)return 0;}
 else {if(pl&&(d->scenario_mask&64))return 0;if(d->scenario_mask&128)return 0;}
 if(!room_shown(pl,floor,d->seen))return 0;
 if(d->bank==255?check_bit((void*)addr(0x98ed2c),d->unlock):bank_bit(d->bank,d->unlock))return 0;
 for(unsigned k=0;k<sizeof(icons)/sizeof(icons[0]);k++)if(icons[k].item==d->key)return icons+k;
 return 0;
}
static const ItemLabel *key_label(unsigned item){
 const ItemLabel *labels=active_item_labels();
 for(unsigned k=0;k<active_item_count();k++)if(labels[k].item==item)return labels+k;
 return 0;
}
// Only key items with a name get a star, as before.
static int key_item_shown(const MapItem *i,unsigned pl,unsigned mpl,unsigned floor){
 return key_label(i->item)&&item_enabled(i->item)&&!map_item(i->item)&&!common_item(i->item)&&i->pl==mpl&&i->floor==floor&&
        room_shown(pl,floor,i->seen)&&!bank_bit(i->bank,i->bit)&&guards_pass(map_item_guards+i->guard_start,i->guard_count);
}
// Marker centre and width; a combined puzzle/key marker sits on its puzzle and the name follows it.
static int key_marker(const MapItem *i,int dx,int dy,int *px,int *py){
 const MapInteraction *pz=combo_of(i);
 if(pz){*px=pz->x+PROJ_CENTRE+dx;*py=pz->y+PROJ_CENTRE+dy;return PUZZLE_KEY_W;}
 *px=i->x+PROJ_CENTRE+dx;*py=i->y+PROJ_CENTRE+dy;
 return (OVERLAY_ICON_TEX/OVERLAY_ICON_SCALE*90+50)/100; // standalone key-item star stays at 90% icon size
}
// Drawn marker box, clamped to the map like the star itself.
static int key_box(const MapItem *i,int dx,int dy,int *x,int *y){
 int px,py,sw=key_marker(i,dx,dy,&px,&py);
 *x=px-sw/2;*y=py-sw/2;
 if(*x<1)*x=1;if(*x>318-sw)*x=318-sw;
 if(*y<1)*y=1;if(*y>238-sw)*y=238-sw;
 return sw;
}
static int document_shown(const MapDocument *m,unsigned pl,unsigned mpl,unsigned floor){
 return m->pl==mpl&&m->floor==floor&&room_shown(pl,floor,m->seen)&&!bank_bit(m->bank,m->bit)&&
        guards_pass(document_guards+m->guard_start,m->guard_count);
}
static int puzzle_drawn(const MapInteraction *m,unsigned pl,unsigned mpl,unsigned floor){
 return puzzles_enabled&&m->pl==mpl&&m->floor==floor&&m->kind==6&&room_shown(pl,floor,m->seen)&&
        guards_pass(interaction_guards+m->guard_start,m->guard_count)&&!puzzle_replaced(m);
}
// High priority first (user 2026-10-26): the native queue (0x416500) pushes onto a list head, so earlier quads draw on
// top. Order: key stars, key names, puzzle diamonds, then (draw_names) room names and low-priority icons; key items are
// never covered, common items and monsters always are. Names ignore those low-priority icons, avoid key and
// puzzle markers, and only lean away from room names, which place themselves afterwards around the names.
static unsigned draw_key_items(unsigned pl,unsigned mpl,unsigned floor,int dx,int dy){
 unsigned n=0,st=cached_texture(&icon_texture,overlay_icon_pixels);
 high_count=0;
 if(!overlay_enabled||!st)return 0;
 for(unsigned j=0;j<sizeof(map_items)/sizeof(map_items[0]);j++){
  const MapItem *i=map_items+j;if(!key_item_shown(i,pl,mpl,floor))continue;
  int x,y,sw=key_box(i,dx,dy,&x,&y),kind=combo_of(i)?15:14;
  for(unsigned q=0;q<sizeof(overlay_icons)/sizeof(overlay_icons[0]);q++)if(overlay_icons[q].kind==kind){
   quad_draw(x,y,sw,sw,overlay_icons[q].u,overlay_icons[q].v,OVERLAY_ICON_TEX,OVERLAY_ICON_TEX,st);break;}
 }
 for(unsigned j=0;j<sizeof(map_interactions)/sizeof(map_interactions[0]);j++){
  const MapInteraction *m=map_interactions+j;
  if(puzzle_drawn(m,pl,mpl,floor))reserve(m->x+PROJ_CENTRE+dx-3,m->y+PROJ_CENTRE+dy-3,6,6);
 }
 // Stand-ins the names steer around and then drop: legend, locks, files/area maps, save/item-box markers, room names.
 unsigned rooms=occupied_count,flags=*(uint32_t*)addr(0x989ed0);
 reserve(1,LEGEND_Y,317,238-LEGEND_Y); // opaque legend rows would cover a translucent name
 hard_count=occupied_count;
 for(unsigned j=0;locks_enabled&&j<sizeof(doors)/sizeof(doors[0]);j++){
  const Icon *i=door_icon(doors+j,pl,mpl,floor,flags);
  if(i){int x,y,w,h;icon_box(doors[j].x+dx,doors[j].y+dy,i,&x,&y,&w,&h);reserve(x,y,w,h);}
 }
 for(unsigned j=0;documents_enabled&&j<sizeof(map_documents)/sizeof(map_documents[0]);j++){
  const MapDocument *m=map_documents+j;if(document_shown(m,pl,mpl,floor))reserve(m->x+PROJ_CENTRE+dx-4,m->y+PROJ_CENTRE+dy-4,8,8);
 }
 for(unsigned j=0;room_names_enabled&&j<sizeof(map_markers)/sizeof(map_markers[0]);j++){
  const MapMarker *m=map_markers+j;
  if(m->pl==mpl&&m->floor==floor&&room_shown(pl,floor,m->seen))reserve(m->x+PROJ_CENTRE+dx-4,m->y+PROJ_CENTRE+dy-4,8,8);
 }
 room_lo=occupied_count;
 for(unsigned j=0;room_names_enabled&&j<active_room_count();j++){
  const RoomName *r=active_room_names()+j;
  if(r->pl!=pl||r->floor!=floor||!room_shown(pl,floor,r->seen))continue;
  int x,y,w,h;room_box(r,active_room_labels()+r->label,dx,dy,&x,&y,&w,&h);reserve(x,y,w,h);
 }
 unsigned names=occupied_count;room_hi=names;
 for(unsigned j=0;j<sizeof(map_items)/sizeof(map_items[0]);j++){
  const MapItem *i=map_items+j;if(!key_item_shown(i,pl,mpl,floor))continue;
  const ItemLabel *l=key_label(i->item);
  unsigned t=cached_texture(active_item_cache(l->page),active_item_pixels(l->page));
  int x,y,sw=key_box(i,dx,dy,&x,&y);
  if(t){item_label_draw(x,y,sw,name_dimension(l->w),name_dimension(l->h),l->u,l->v,l->w,l->h,t);n++;}
 }
 // Drop the room-name stand-ins; the real room names are placed later and avoid the key-item names.
 for(unsigned j=names;j<occupied_count;j++)occupied[rooms+j-names]=occupied[j];
 occupied_count-=names-rooms;
 hard_count=room_lo=room_hi=0;
 // Diamonds after the names. Names steer around them; where a name still overlaps one, the key item wins and that
 // diamond is skipped (translucent names cannot be drawn over it; user 2026-10-26).
 unsigned name_end=occupied_count;
 for(unsigned j=0;j<sizeof(map_interactions)/sizeof(map_interactions[0]);j++){
  const MapInteraction *m=map_interactions+j;if(!puzzle_drawn(m,pl,mpl,floor))continue;
  int x=m->x+PROJ_CENTRE+dx-3,y=m->y+PROJ_CENTRE+dy-3,hidden=0;
  for(unsigned k=rooms;k<name_end;k++){const Bounds *r=occupied+k;if(x<r->x+r->w&&r->x<x+6&&y<r->y+r->h&&r->y<y+6)hidden=1;}
  if(hidden)continue;
  for(unsigned k=0;k<sizeof(overlay_icons)/sizeof(overlay_icons[0]);k++)if(overlay_icons[k].kind==12){
   const OverlayIcon*i=overlay_icons+k;
   quad_draw(m->x+PROJ_CENTRE+dx-3,m->y+PROJ_CENTRE+dy-3,6,6,i->u,i->v,OVERLAY_ICON_TEX,OVERLAY_ICON_TEX,st);break;
  }
 }
 high_count=occupied_count;
 return n;
}
static void draw_names(unsigned mode){
 unsigned floor=*(unsigned char*)addr(0x691f7a);
 unsigned flags=*(uint32_t*)addr(0x989ed0),pl=flags>>31,mpl=marker_pl(pl),npl=monster_pl(pl);
 if(frames++%120==0)log_line("entry floor=%u mapmode=%u flags=%08lx\n",floor,mode,(unsigned long)flags);
 // Mode0 is interactive; mode2/3 are the map exit transition.
 if(mode!=0||floor>=20)return;
 occupied_count=0;
 unsigned tex=overlay_enabled&&locks_enabled?get_texture():0;
 int dx=*(short*)addr(0x691fb8),dy=*(short*)addr(0x691fba);unsigned shown=0,pickups=0,names=0;
 const RoomName *active_names=active_room_names();
 const RoomLabel *active_labels=active_room_labels();
 collect_combos(pl,mpl,floor);
 pickups=draw_key_items(pl,mpl,floor,dx,dy);
 drawing_names=1;
 // Room names after key items (those stay on top); markers and low-priority icons queue later, underneath.
 for(unsigned j=0;overlay_enabled&&room_names_enabled&&j<active_room_count();j++){
  const RoomName *r=active_names+j;
  if(r->pl!=pl||r->floor!=floor||!room_shown(pl,floor,r->seen))continue;
  const RoomLabel *l=active_labels+r->label;
  unsigned t=cached_texture(active_room_cache(l->page),active_room_pixels(l->page));
  if(!t)continue;
  if(r->lx0|r->ly0|r->lx1|r->ly1){ // axis-aligned leader line, opaque texel (0,0)
   int x0=r->lx0<r->lx1?r->lx0:r->lx1,y0=r->ly0<r->ly1?r->ly0:r->ly1;
   quad_draw(x0+dx,y0+dy,(r->lx0>r->lx1?r->lx0-r->lx1:r->lx1-r->lx0)+1,(r->ly0>r->ly1?r->ly0-r->ly1:r->ly1-r->ly0)+1,0,0,1,1,t);
  }
  int x,y,w,h;room_box(r,l,dx,dy,&x,&y,&w,&h);
  quad_draw(x,y,w,h,l->u,l->v,l->w,l->h,t);names++;
 }
 drawing_names=0;
 // Typewriter / item-box icons share the room-name toggle and visited-room gate.
 unsigned marks=0,docmarks=0;
 for(unsigned j=0;overlay_enabled&&room_names_enabled&&j<sizeof(map_markers)/sizeof(map_markers[0]);j++){
  const MapMarker *m=map_markers+j;
  if(m->pl!=mpl||m->floor!=floor||!room_shown(pl,floor,m->seen))continue;
  unsigned t=cached_texture(&icon_texture,overlay_icon_pixels);
  if(!t)break;
  for(unsigned k=0;k<sizeof(overlay_icons)/sizeof(overlay_icons[0]);k++)if(overlay_icons[k].kind==m->kind){
   const OverlayIcon *i=overlay_icons+k;int w=OVERLAY_ICON_TEX/OVERLAY_ICON_SCALE;
   // Exact spot, no collision displacement (it pushed icons into neighbouring rooms).
   if(!under_high(m->x+PROJ_CENTRE+dx-w/2,m->y+PROJ_CENTRE+dy-w/2,w,w))quad_draw(m->x+PROJ_CENTRE+dx-w/2,m->y+PROJ_CENTRE+dy-w/2,w,w,i->u,i->v,OVERLAY_ICON_TEX,OVERLAY_ICON_TEX,t);marks++;break;
  }
 }
 for(unsigned j=0;overlay_enabled&&documents_enabled&&j<sizeof(map_documents)/sizeof(map_documents[0]);j++){
  const MapDocument *d=map_documents+j;
  if(d->pl!=mpl||d->floor!=floor||!room_shown(pl,floor,d->seen)||bank_bit(d->bank,d->bit)||
     !guards_pass(document_guards+d->guard_start,d->guard_count))continue;
  unsigned t=cached_texture(&icon_texture,overlay_icon_pixels);
  if(!t)break;
  for(unsigned k=0;k<sizeof(overlay_icons)/sizeof(overlay_icons[0]);k++)if(overlay_icons[k].kind==11){
   const OverlayIcon *i=overlay_icons+k;int w=OVERLAY_ICON_TEX/OVERLAY_ICON_SCALE;
   if(!under_high(d->x+PROJ_CENTRE+dx-w/2,d->y+PROJ_CENTRE+dy-w/2,w,w))quad_draw(d->x+PROJ_CENTRE+dx-w/2,d->y+PROJ_CENTRE+dy-w/2,w,w,i->u,i->v,OVERLAY_ICON_TEX,OVERLAY_ICON_TEX,t);docmarks++;break;
  }
 }
 for(unsigned j=0;overlay_enabled&&locks_enabled&&j<sizeof(doors)/sizeof(doors[0]);j++){
  const Door*d=doors+j;const Icon *i=door_icon(d,pl,mpl,floor,flags);if(!i)continue;
  int x,y,w,h;icon_box(d->x+dx,d->y+dy,i,&x,&y,&w,&h);
  if(!under_high(x,y,w,h)){quad_draw(x,y,w,h,i->u,i->v,i->w,i->h,tex);shown++;}
 }
 unsigned monsters=0;
 for(unsigned j=0;overlay_enabled&&monsters_enabled&&j<sizeof(map_monsters)/sizeof(map_monsters[0]);j++){
  const MapMonster *m=map_monsters+j;
  if(m->pl!=npl||m->floor!=floor||!room_shown(pl,floor,m->seen)||monster_dead(m)||
     !guards_pass(monster_guards+m->guard_start,m->guard_count))continue;
  unsigned t=cached_texture(&icon_texture,overlay_icon_pixels);
  if(!t)break;
  for(unsigned k=0;k<sizeof(overlay_icons)/sizeof(overlay_icons[0]);k++)if(overlay_icons[k].kind==MONSTER_KIND+m->cat){
   const OverlayIcon*i=overlay_icons+k;
   if(!under_high(m->x+PROJ_CENTRE+dx-3,m->y+PROJ_CENTRE+dy-3,6,6))quad_draw(m->x+PROJ_CENTRE+dx-3,m->y+PROJ_CENTRE+dy-3,6,6,i->u,i->v,OVERLAY_ICON_TEX,OVERLAY_ICON_TEX,t);monsters++;break;
  }
 }
 // Key items and puzzle diamonds were drawn first (draw_key_items); only common/map items remain.
 for(unsigned j=0;overlay_enabled&&j<sizeof(map_items)/sizeof(map_items[0]);j++){
  const MapItem *i=map_items+j;
  if(!item_enabled(i->item)||i->pl!=mpl||i->floor!=floor||!room_shown(pl,floor,i->seen)||bank_bit(i->bank,i->bit))continue;
  if(!guards_pass(map_item_guards+i->guard_start,i->guard_count))continue;
  if(map_item(i->item)||common_item(i->item)){
   unsigned t=cached_texture(&icon_texture,overlay_icon_pixels);
   if(!t)break;
   for(unsigned q=0;q<sizeof(overlay_icons)/sizeof(overlay_icons[0]);q++)if(overlay_icons[q].kind==((i->item>=200&&i->item<=205)?13:100+i->item)){
    const OverlayIcon *icon=overlay_icons+q;int w=(OVERLAY_ICON_TEX/OVERLAY_ICON_SCALE*90+50)/100;
    int x=i->x+PROJ_CENTRE+dx-w/2,y=i->y+PROJ_CENTRE+dy-w/2;
    // Area maps are progression pickups: when a diamond/star covers the spot (East Office safe holds the police map),
    // show the map as a badge half under its lower-right corner instead of hiding it (user 2026-10-28). The marker it
    // belongs to (the box holding the pickup point) stays on top; generate_room_names keeps the badge box clear.
    int cx=x+w/2,cy=y+w/2,own=map_item(i->item)&&under_high(x,y,w,w);
    if(own){x+=MAP_BADGE;y+=MAP_BADGE;}
    if(own?!under_high_except(x,y,w,w,cx,cy):!under_high(x,y,w,w))quad_draw(x,y,w,w,icon->u,icon->v,OVERLAY_ICON_TEX,OVERLAY_ICON_TEX,t);pickups++;break;
   }
  }
 }
 help_draw();
 if((frames-1)%120==0)log_line("map floor=%u locks=%u items=%u docs=%u rooms=%u icons=%u monsters=%u enabled=%u tinted=%u texture=%u\n",floor,shown,pickups,docmarks,names,marks,monsters,puzzles_enabled,tinted,tex);
 tinted=0;
}
__declspec(dllexport) unsigned __cdecl KeyMapTestUpload(void){test_texture=0;texture=0;return get_texture();}
__declspec(dllexport) unsigned __cdecl KeyMapTestUploadPage(unsigned i){
 // 0=key atlas, then active-language room/item pages and the icon page.
 if(i==0)return create_texture(atlas_pixels);
 unsigned rp=english_enabled?ROOM_LABEL_PAGE_COUNT_EN:ROOM_LABEL_PAGE_COUNT_KO;
 unsigned ip=english_enabled?ITEM_LABEL_PAGE_COUNT_EN:ITEM_LABEL_PAGE_COUNT_KO;
 if(i<=rp)return create_texture(active_room_pixels(i-1));
 if(i-1-rp<ip)return create_texture(active_item_pixels(i-1-rp));
 if(i==1+rp+ip)return create_texture(overlay_icon_pixels);
 return 0;
}
__declspec(dllexport) void __cdecl KeyMapTestTexture(unsigned id){test_texture=1;texture=id;}
__declspec(dllexport) void __cdecl KeyMapTestInit(unsigned char *g){game=g;flat_rect=(void*)addr(0x441170);check_bit=(void*)addr(0x503170);sprite_draw=(void*)addr(0x440280);}
__declspec(dllexport) uintptr_t __cdecl KeyMapTestFillHook(void){return (uintptr_t)fill_stub;}
__declspec(dllexport) void __cdecl KeyMapTestDraw(void){draw_names(*(unsigned char*)addr(0x691f62));}
__declspec(dllexport) void __cdecl KeyMapTestToggle(unsigned mode,int down){update_toggle(mode,down);}
__declspec(dllexport) int __cdecl KeyMapTestState(void){return overlay_enabled|(room_names_enabled<<1)|(locks_enabled<<2)|(items_enabled<<3)|(documents_enabled<<4);}
__declspec(dllexport) int __cdecl KeyMapTestInteractionStage(void){return puzzles_enabled;}
__declspec(dllexport) int __cdecl KeyMapTestLanguage(void){return english_enabled;}
__declspec(dllexport) int __cdecl KeyMapTestMonsters(void){return monsters_enabled;}
__declspec(dllexport) int __cdecl KeyMapTestCommon(void){return common_enabled;}
__declspec(dllexport) unsigned __cdecl KeyMapTestOpacity(void){return name_opacity;}
__declspec(dllexport) unsigned __cdecl KeyMapTestOpacityValue(int v){return opacity_value(v);}
__declspec(dllexport) unsigned __cdecl KeyMapTestScope(void){return scope;}
__declspec(dllexport) unsigned __cdecl KeyMapTestSize(void){return name_size;}
__declspec(dllexport) unsigned __cdecl KeyMapTestSizeValue(int v){return size_value(v);}
static unsigned map_keys_down(void){return
 ((GetAsyncKeyState('0')&0x8000)?1:0)|((GetAsyncKeyState('1')&0x8000)?2:0)|
 ((GetAsyncKeyState('2')&0x8000)?4:0)|((GetAsyncKeyState('3')&0x8000)?8:0)|
 ((GetAsyncKeyState('4')&0x8000)?16:0)|((GetAsyncKeyState('9')&0x8000)?32:0)|
 ((GetAsyncKeyState('5')&0x8000)?64:0)|((GetAsyncKeyState('6')&0x8000)?128:0)|
 ((GetAsyncKeyState('7')&0x8000)?256:0)|((GetAsyncKeyState(VK_OEM_PLUS)|GetAsyncKeyState(VK_ADD))&0x8000?512:0)|
 ((GetAsyncKeyState(VK_OEM_MINUS)|GetAsyncKeyState(VK_SUBTRACT))&0x8000?1024:0)|((GetAsyncKeyState(VK_SHIFT)&0x8000)?2048:0)|((GetAsyncKeyState('8')&0x8000)?4096:0);}
// Native status-menu/map animation shares sprite storage. Repair missing UI templates before their draw.
static void ensure_native_ui(void){
 int valid=1;
 for(unsigned n=0;n<4;n++){
  const unsigned char *p=(void*)addr(0x8c28f8+n*20),*d=(void*)addr(n<2?0x53dae4:0x53dae0);
  if(p[3]!=4||p[0xc]!=d[0]||p[0xd]!=d[1]||*(unsigned short*)(p+0x10)!=d[2]||*(unsigned short*)(p+0x12)!=d[3])valid=0;
 }
 if(!valid){
  void (__cdecl *prepare)(void)=(void*)addr(0x4fa7d0);prepare();
  log_line("rebuilt native map UI floor=%u mode=%u titleTex=%u compassTex=%u\n",*(unsigned char*)addr(0x691f7a),*(unsigned char*)addr(0x691f62),*(unsigned*)addr(0x67c7d8+30*12),*(unsigned*)addr(0x67c7d8+31*12));
 }
}
static int draw_all_room_outlines(void){
 unsigned floor=*(unsigned char*)addr(0x691f7a),pl=(*(uint32_t*)addr(0x989ed0)>>31)&1;
 const unsigned char *f=(const unsigned char*)addr(pl?0x53eb98:0x53eaf8)+floor*8;
 unsigned char *rooms=(unsigned char*)*(uint32_t*)f;unsigned count=f[4],bit=f[5];
 uint32_t *maps=(uint32_t*)addr(0x98ec1c)+(bit>>5),old_map=*maps;unsigned map_mask=0x80000000u>>(bit&31);unsigned char mask[255][2];
 if(!rooms||!count||count>255)return 0;
 DWORD old_protect;size_t bytes=(size_t)count*16;
 if(!VirtualProtect(rooms,bytes,PAGE_READWRITE,&old_protect))return 0;
 *maps|=map_mask;
 for(unsigned i=0;i<count;i++){mask[i][0]=rooms[i*16+14];mask[i][1]=rooms[i*16+15];rooms[i*16+14]=rooms[i*16+15]=0;}
 map_draw();
 for(unsigned i=0;i<count;i++){rooms[i*16+14]=mask[i][0];rooms[i*16+15]=mask[i][1];}
 DWORD unused;VirtualProtect(rooms,bytes,old_protect,&unused);*maps=old_map;return 1;
}
static void draw_map(unsigned mode){update_toggle(mode,map_keys_down());ensure_native_ui();if(scope!=3||!draw_all_room_outlines())map_draw();draw_names(mode);}
// The status-screen selection handler 0x4fa240 draws at phase3; the ordinary map handler draws at phase0.
static void __cdecl hook_status_selection(void){draw_map(0);}
static void __cdecl hook_map(void){draw_map(*(unsigned char*)addr(0x691f62));}
static void __cdecl hook_status_entry(void){draw_map(0);}
__declspec(dllexport) void __cdecl KeyMapTestStatusDraw(void){draw_names(0);}
__declspec(dllexport) void __cdecl KeyMapTestEnsureUI(void){ensure_native_ui();}
// Status-map area/floor selection. Native Up/Down (0x4fb4df) needs bank0 bit0, skips floors 0/1 and only walks the
// chains 4-3-2-5, 7-8, 13..17 (0x53da28/0x53da40). Here Left/Right pick the area, Up/Down the floor, top to bottom,
// visited floors only (the same 0x98ec00 floor bit the native chains test); no wrap-around.
static const unsigned char floor_order[20]={0,1, 4,3,2,5,6, 7,8, 9,10,11,12, 13,14,15,16,17, 18,19};
static const unsigned char area_start[7]={0,2,7,9,13,18,20}; // city, police station, sewer, factory, lab, train
static int floor_visited(unsigned f){return check_bit((void*)addr(0x98ec00),f)!=0;}
static int area_floor(unsigned area,unsigned player){
 for(unsigned p=area_start[area];p<area_start[area+1];p++)if(floor_order[p]==player)return player;
 // ponytail: top-most visited floor; remember the last viewed floor per area if this feels wrong
 for(unsigned p=area_start[area];p<area_start[area+1];p++)if(floor_visited(floor_order[p]))return floor_order[p];
 return -1;
}
static unsigned player_floor(void){
 unsigned (__cdecl *floor_of)(int,int)=(void*)addr(0x4faf80); // native stage/room -> floor (0x4fb673)
 return floor_of(*(short*)addr(0x98eb14),*(short*)addr(0x98eb16));
}
static int floor_pos(unsigned f){for(int p=0;p<20;p++)if(floor_order[p]==f)return p;return -1;}
static unsigned pos_area(int pos){unsigned area=0;while(area_start[area+1]<=(unsigned)pos)area++;return area;}
static int area_step(unsigned area,int step,unsigned player){
 for(int a=(int)area+step;a>=0&&a<6;a+=step){int f=area_floor(a,player);if(f>=0)return f;}
 return -1;
}
static unsigned map_nav(unsigned pad){
 unsigned cur=*(unsigned char*)addr(0x691f7a);int pos=floor_pos(cur),next=-1;
 if(pos<0)return 0;
 unsigned area=pos_area(pos);
 if(pad&0x1000){for(int p=pos;p-->(int)area_start[area];)if(floor_visited(floor_order[p])){next=floor_order[p];break;}}
 else if(pad&0x4000){for(unsigned p=pos+1;p<area_start[area+1];p++)if(floor_visited(floor_order[p])){next=floor_order[p];break;}}
 else if(pad&0xa000)next=area_step(area,pad&0x2000?1:-1,player_floor());
 if(next<0||(unsigned)next==cur)return 0;
 // Same as native 0x4fb592: new floor, cursor sound, state 1 reloads the floor's map file.
 void (__cdecl *sound)(unsigned,unsigned)=(void*)addr(0x4ed950);
 *(unsigned char*)addr(0x691f7a)=(unsigned char)next;*(unsigned char*)addr(0x691f62)=1;sound(0x4040000,0);
 return 1;
}
// Area arrows as in the RE1 map mode (gen_assets.py nav triangles): 9x12 map px, green with a dark outline, at x 5 / 315
// on the vertical centre. Drawn at 8 texels per map pixel from a runtime page. They pulse with the native player cursor:
// its colour is 0x28 + the 2..82 triangle counter 0x691f88 (step 2 per frame, 0x4fb49a; used at 0x4faaa4; 0x80 neutral).
#define NAV_W 9
#define NAV_H 12
#define NAV_S 8
static unsigned short nav_pixels[65536]; // kept alive: Marni may re-read source pixels
static int nav_inside(float x,float y,const float *t){
 float s=0;int pos=0,neg=0;
 for(int i=0;i<3;i++){const float *a=t+2*i,*b=t+2*((i+1)%3);s=(b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0]);pos|=s>0;neg|=s<0;}
 return !(pos&&neg);
}
static void nav_build(void){
 const float w=NAV_W*NAV_S,h=NAV_H*NAV_S,outer[6]={w-1,0,w-1,h-1,0,h/2};
 float inner[6];for(int i=0;i<6;i+=2){inner[i]=outer[i]+(w/2-outer[i])*0.18f;inner[i+1]=outer[i+1]+(h/2-outer[i+1])*0.18f;}
 for(int y=0;y<h;y++)for(int x=0;x<w;x++){
  unsigned short c=nav_inside(x+.5f,y+.5f,inner)?0x2347:nav_inside(x+.5f,y+.5f,outer)?0x0421:0; // RE1 GREEN / BLACK
  nav_pixels[y*256+x]=c;nav_pixels[y*256+128+(int)w-1-x]=c; // left cell at u0, mirrored right cell at u128
 }
}
static void nav_arrows_draw(void){
 int pos=floor_pos(*(unsigned char*)addr(0x691f7a));
 if(pos<0)return;
 unsigned area=pos_area(pos),player=player_floor();
 int left=area_step(area,-1,player)>=0,right=area_step(area,1,player)>=0;
 if(!left&&!right)return;
 if(!nav_pixels[NAV_H*NAV_S/2*256+NAV_S])nav_build();
 unsigned tex=cached_texture(&nav_texture,nav_pixels);
 unsigned shade=(*(unsigned char*)addr(0x691f88)+0x28)&0xff;
 quad_color=0xff000000|shade<<16|shade<<8|shade;
 if(left)quad_draw(5,120-NAV_H/2,NAV_W,NAV_H,0,0,NAV_W*NAV_S,NAV_H*NAV_S,tex);
 if(right)quad_draw(315-NAV_W,120-NAV_H/2,NAV_W,NAV_H,128,0,NAV_W*NAV_S,NAV_H*NAV_S,tex);
 quad_color=0;
}
// 0x4fb7e7 runs after the status-map handler (index 2 in 0x53db1c) and, after a floor reload, again within the same
// frame while 0x9885fc still holds the press: act on newly pressed directions only, or one press moves two floors.
static unsigned nav_pad_was;
static unsigned nav_press(unsigned pad){pad&=0xf000;unsigned pressed=pad&~nav_pad_was;nav_pad_was=pad;return map_nav(pressed);}
static void __cdecl hook_status_map(void){
 if(*(unsigned char*)addr(0x691f61)!=2){hook_map();return;}
 if(nav_press(*(uint32_t*)addr(0x9885fc)))return; // the floor's map is reloaded first; native skips this frame's draw too
 hook_map();nav_arrows_draw();
}
__declspec(dllexport) unsigned __cdecl KeyMapTestNav(unsigned pad){return map_nav(pad);}
__declspec(dllexport) unsigned __cdecl KeyMapTestNavPress(unsigned pad){return nav_press(pad);}
__declspec(dllexport) uintptr_t __cdecl KeyMapTestNavPixels(void){nav_build();return (uintptr_t)nav_pixels;}
BOOL WINAPI DllMain(HINSTANCE module,DWORD reason,LPVOID reserved){
 (void)reserved;if(reason!=DLL_PROCESS_ATTACH)return TRUE;
 DisableThreadLibraryCalls(module);game=(unsigned char*)GetModuleHandleW(NULL);
 char own[MAX_PATH];GetModuleFileNameA(module,own,sizeof(own));char *slash=NULL;for(char *p=own;*p;p++)if(*p=='\\')slash=p;
 if(slash){lstrcpyA(slash+1,"RE2.AnnotatedMap.ini");lstrcpyA(settings_path,own);lstrcpyA(slash+1,"RE2.AnnotatedMap.log");}else{lstrcpyA(own,"RE2.AnnotatedMap.log");lstrcpyA(settings_path,"RE2.AnnotatedMap.ini");}
 load_settings();
 logfile=CreateFileA(own,GENERIC_WRITE,FILE_SHARE_READ,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
 const unsigned sites[]={0x4fa552,0x4fb60b,0x4fb7e7,0x4faf3f},targets[]={0x4fa990,0x4fa990,0x4fa990,0x440280};
 const uintptr_t hooks[]={(uintptr_t)hook_status_selection,(uintptr_t)hook_status_entry,(uintptr_t)hook_status_map,(uintptr_t)fill_stub};
 for(unsigned i=0;i<4;i++){
  unsigned char *site=(unsigned char*)addr(sites[i]);
  if(site[0]!=0xe8 || (uintptr_t)(site+5)+(int32_t)*(int32_t*)(site+1)!=addr(targets[i])){
   log_line("unsupported map call at %08x; no patch applied\n",sites[i]);return TRUE;
  }
 }
 // Fill site: push 0; push 10; push 0x20; push esi; call 0x440280; add esp,16 (room loop 0x4fabf4..0x4faf4e).
 const unsigned char fill[]={0x6a,0x00,0x6a,0x0a,0x6a,0x20,0x56};
 if(!equal((void*)addr(0x4faf38),fill,sizeof(fill))||!equal((void*)addr(0x4faf44),"\x83\xc4\x10",3)){log_line("unsupported room fill call; no patch applied\n");return TRUE;}
 const unsigned char bit[]={0x8b,0x54,0x24,0x08,0xb8,0x00,0x00,0x00,0x80};
 if(!equal((void*)addr(0x503170),bit,sizeof(bit))){{log_line("unsupported bit checker; no patch applied\n");}return TRUE;}
 // Native status-map Up/Down (bank0 bit0 set in the police station/lab): jns 0x4fb5aa -> jmp, map_nav owns floors.
 const unsigned char native_nav[]={0x0f,0x89,0xbe,0x00,0x00,0x00};
 if(!equal((void*)addr(0x4fb4e6),native_nav,sizeof(native_nav))){log_line("unsupported native floor switch; no patch applied\n");return TRUE;}
 map_draw=(void*)addr(0x4fa990);flat_rect=(void*)addr(0x441170);check_bit=(void*)addr(0x503170);sprite_draw=(void*)addr(0x440280);
 // Validate every call before mutation and acquire permissions for all four sites.
 DWORD olds[4];unsigned acquired=0;
 for(;acquired<4;acquired++){
  if(!VirtualProtect((void*)addr(sites[acquired]),5,PAGE_EXECUTE_READWRITE,olds+acquired))break;
 }
 if(acquired!=4){DWORD unused;for(unsigned i=0;i<acquired;i++)VirtualProtect((void*)addr(sites[i]),5,olds[i],&unused);log_line("map code permissions failed; no patch applied\n");return TRUE;}
 {DWORD old,unused;unsigned char *site=(unsigned char*)addr(0x4fb4e6);
  if(VirtualProtect(site,6,PAGE_EXECUTE_READWRITE,&old)){
   site[0]=0xe9;*(int32_t*)(site+1)=0x4fb5aa-(0x4fb4e6+5);site[5]=0x90;
   VirtualProtect(site,6,old,&unused);FlushInstructionCache(GetCurrentProcess(),site,6);
  }else log_line("native floor switch permissions failed; mod and native Up/Down may both act\n");}
 for(unsigned i=0;i<4;i++){
  unsigned char *site=(unsigned char*)addr(sites[i]);
  *(int32_t*)(site+1)=(int32_t)(hooks[i]-(uintptr_t)(site+5));
  DWORD unused;VirtualProtect(site,5,olds[i],&unused);FlushInstructionCache(GetCurrentProcess(),site,5);
 }
 log_line("RE2.KeyMapNames bilingual build, 0-3 overlays, 9 language, settings loaded; labels=%u\n",(unsigned)(sizeof(doors)/sizeof(doors[0])));
 return TRUE;
}
