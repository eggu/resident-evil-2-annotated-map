#include <windows.h>
#include <stdint.h>
#include <stdarg.h>
#include "atlas.h"
#include "key_art.h"
#include "bilingual_assets.h"
#include "items.h"
#include "overlay_data.h"
#include "overlay_icons.h"
#include "fill_masks.h"
#include "rank_glyphs.h"
#include "monsters.h"
#include "sd_assets.h"
#define MONSTER_KIND 50 /* overlay icon kind of monster category 0 */
typedef struct { unsigned char pl,floor; short x,y; unsigned char seen,unlock,key,scenario_mask,bank; short x1,y1,x2,y2; unsigned char seen2; } Door;
/* x,y native lock marker on the door; x1,y1 the door AOT in its own room; x2,y2 its arrival point in room seen2 (255 = none) */
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
static int english_enabled=1,monsters_enabled=0,common_enabled=0,events_enabled=0;
#define EVENT_KIND 20 /* MapInteraction.kind of a story-scene marker (extract_overlay.EVENT_KIND) */
static unsigned scope=1; /* [8] 1 visited rooms, 2 + rooms revealed by the floor map, 3 all rooms */
static unsigned name_opacity=70,name_size=100;
// RE0 HD map mod controls (user 2026-11-07): [H] item names (off until pressed), icon size/opacity with the modifier.
// The modifier is Shift unless the INI says Ctrl: the game binds Ctrl (config.ini KeyDef 0x11), not Shift.
static unsigned icon_size=100,icon_opacity=80;
// [H] marker names, 3 states (user 2026-11-08): 0 hidden, 1 all, 2 all except common items. Stored as ItemNames=0/1/2, so the
// old on/off values (0 off, 1 on) keep their meaning: old on -> all, old off -> hidden.
enum { NAMES_OFF,NAMES_ALL,NAMES_NO_COMMON };
static int item_names_enabled,modifier_ctrl,lock_side;
static int rank_enabled,legend_enabled=1;
// SD mode (2026-11-12, common/SD-MAP-PORTING.md): without the HD pack the map draws 1:1 pixel markers and Galmuri9 names from
// sd_assets.h. Fixed for the session once the first map draws. INI DisplayMode: Auto, HD or SD.
static int display_mode,sd_mode=-1; // display_mode 0 Auto, 1 HD, 2 SD
#define sd_on() (sd_mode>0)
static char config_path[MAX_PATH];
static unsigned size_value(int value){if(value<50)value=50;if(value>200)value=200;return (unsigned)(value+5)/10*10;}
static unsigned icon_size_value(int value){if(value<50)value=50;if(value>200)value=200;return (unsigned)(value+5)/10*10;}
static int drawing_names,drawing_icons;
static int quad_mode; // 0 queue and reserve, 1 reserve only (placement pass), 2 queue only (reserved by the earlier pass)
static unsigned opacity_value(int value){if(value<10)value=10;if(value>100)value=100;return (unsigned)(value+5)/10*10;}
static unsigned toggle_was_down;
// 2x map zoom, session only. Native map has no scale: after map_draw the queued packets are rewritten (zoom_packets).
static int zoom_on,view_x,view_y,zoom_center; // view = top-left of the 320x240 window on the doubled 640x480 map
#define MX(v) (zoom_on?2*((v)+dx)-view_x:(v)+dx)
#define MY(v) (zoom_on?2*((v)+dy)-view_y:(v)+dy)
// Names and icons follow the map zoom like the RE0 HD map mod's name_zoom (Z0 = 0.7: the zoomed-out map shows 70% of the
// fully zoomed size), with 1x kept at the size users set: 2x draws them 1/0.7 = 143% (user 2026-11-07: icons stayed the
// same size when zoomed). The map itself doubles, so they still grow less than the map.
#define ZOOM_GAIN 143
static int zoom_gain(void){return zoom_on?ZOOM_GAIN:100;}
// Name size 100% is the former 80% (user 2026-11-08: the old default looked too large): scale = size x 0.8 / 4 (label raster scale) x zoom.
static int name_dimension(unsigned pixels){return (int)(pixels*name_size*(unsigned)zoom_gain()*4+100000)/200000;}
static int isz(int pixels){if(sd_on())return 9;int v=(pixels*(int)icon_size*zoom_gain()+5000)/10000;return v<1?1:v;} // marker side: icon size x zoom
static char settings_path[MAX_PATH];
// Version 2 (2026-11-07) adds ItemNames, IconSize, IconOpacity, Modifier and LockSide. No stored value changed scale,
// so a file without Version keeps its values and is rewritten once with Version and the new keys. Version 3 (2026-11-08):
// ItemNames gains the value 2 (no common items); 0 and 1 read as before, and the file is rewritten once with Version=3.
// Version 4 (2026-11-08): the number keys were renumbered ([6] events, common items [7], enemies [8], scope [9], language on the
// backslash key); toggles are stored by name so they keep their values, Events is new, and NameSize is re-based (100% is the
// former 80%): an older file's NameSize is converted once so the visible size stays.
// Version 5 (2026-11-13, user request): lock markers sit beside the door in the room not entered yet by default (LockSide=1). Version 4
// and older files stored LockSide=0 as the default, so their value is replaced by 1 once; set it back to 0 afterwards to keep it on the door.
#define SETTINGS_VERSION 5
// Atomic save: the keys go into a copy of the INI (its comments kept), which then replaces it; on failure the old file stays.
static int save_settings(void){
 if(!settings_path[0])return 0;
 char tmp[MAX_PATH+4],value[8];
 if(lstrlenA(settings_path)+4>=MAX_PATH)return 0;
 lstrcpyA(tmp,settings_path);lstrcatA(tmp,".tmp");
 CopyFileA(settings_path,tmp,FALSE); // a missing INI just starts an empty copy
 const char *keys[]={"All","Rooms","Locks","Items","Documents","Puzzles","English","Enemies","CommonItems","Rank","Legend","LockSide","Events"};
 int values[]={overlay_enabled,room_names_enabled,locks_enabled,items_enabled,documents_enabled,puzzles_enabled,english_enabled,monsters_enabled,common_enabled,rank_enabled,legend_enabled,lock_side,events_enabled};
 int ok=1;
 for(unsigned i=0;i<sizeof(keys)/sizeof(keys[0]);i++){value[0]=values[i]?'1':'0';value[1]=0;ok&=WritePrivateProfileStringA("MapOverlay",keys[i],value,tmp)!=0;}
 const char *nums[]={"Version","Scope","NameSize","NameOpacity","IconSize","IconOpacity"};
 unsigned numbers[]={SETTINGS_VERSION,scope,name_size,name_opacity,icon_size,icon_opacity};
 for(unsigned i=0;i<sizeof(nums)/sizeof(nums[0]);i++){wsprintfA(value,"%u",numbers[i]);ok&=WritePrivateProfileStringA("MapOverlay",nums[i],value,tmp)!=0;}
 value[0]=(char)('0'+item_names_enabled);value[1]=0;ok&=WritePrivateProfileStringA("MapOverlay","ItemNames",value,tmp)!=0;
 ok&=WritePrivateProfileStringA("MapOverlay","Modifier",modifier_ctrl?"Ctrl":"Shift",tmp)!=0;
 ok&=WritePrivateProfileStringA("MapOverlay","DisplayMode",display_mode==2?"SD":display_mode==1?"HD":"Auto",tmp)!=0;
 if(ok)ok=MoveFileExA(tmp,settings_path,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)!=0;
 if(!ok){DeleteFileA(tmp);log_line("settings save failed; previous INI kept\n");}
 return ok;
}
// Returns 1 when the file predates SETTINGS_VERSION and should be rewritten once.
static int load_settings(void){
 overlay_enabled=GetPrivateProfileIntA("MapOverlay","All",1,settings_path)!=0;
 room_names_enabled=GetPrivateProfileIntA("MapOverlay","Rooms",1,settings_path)!=0;
 locks_enabled=GetPrivateProfileIntA("MapOverlay","Locks",0,settings_path)!=0;
 items_enabled=GetPrivateProfileIntA("MapOverlay","Items",0,settings_path)!=0;
 documents_enabled=GetPrivateProfileIntA("MapOverlay","Documents",0,settings_path)!=0;
 puzzles_enabled=GetPrivateProfileIntA("MapOverlay","Puzzles",0,settings_path)!=0;
 english_enabled=GetPrivateProfileIntA("MapOverlay","English",1,settings_path)!=0;
 monsters_enabled=GetPrivateProfileIntA("MapOverlay","Enemies",0,settings_path)!=0;
 common_enabled=GetPrivateProfileIntA("MapOverlay","CommonItems",0,settings_path)!=0;
 {int v=(int)GetPrivateProfileIntA("MapOverlay","NameSize",0,settings_path); // 0: no saved value, the new default
  if(!v)v=100;else if(GetPrivateProfileIntA("MapOverlay","Version",0,settings_path)<4)v=(v*100+40)/80; // a saved old value: old 80% is the new 100%
  name_size=size_value(v);}
 events_enabled=GetPrivateProfileIntA("MapOverlay","Events",0,settings_path)!=0;
 rank_enabled=GetPrivateProfileIntA("MapOverlay","Rank",0,settings_path)!=0;
 legend_enabled=GetPrivateProfileIntA("MapOverlay","Legend",1,settings_path)!=0;
 name_opacity=opacity_value((int)GetPrivateProfileIntA("MapOverlay","NameOpacity",70,settings_path));
 scope=GetPrivateProfileIntA("MapOverlay","Scope",1,settings_path);if(scope<1||scope>3)scope=1;
 {int v=(int)GetPrivateProfileIntA("MapOverlay","ItemNames",0,settings_path);item_names_enabled=v==2?NAMES_NO_COMMON:v!=0?NAMES_ALL:NAMES_OFF;}
 icon_size=icon_size_value((int)GetPrivateProfileIntA("MapOverlay","IconSize",100,settings_path));
 icon_opacity=opacity_value((int)GetPrivateProfileIntA("MapOverlay","IconOpacity",80,settings_path));
 lock_side=GetPrivateProfileIntA("MapOverlay","Version",0,settings_path)<5||GetPrivateProfileIntA("MapOverlay","LockSide",1,settings_path)!=0;
 {char m[8]={0};GetPrivateProfileStringA("MapOverlay","DisplayMode","Auto",m,sizeof(m),settings_path);display_mode=lstrcmpiA(m,"SD")==0?2:lstrcmpiA(m,"HD")==0?1:0;}
 char mod[8]={0};GetPrivateProfileStringA("MapOverlay","Modifier","Shift",mod,sizeof(mod),settings_path);
 modifier_ctrl=lstrcmpiA(mod,"Ctrl")==0;
 return GetPrivateProfileIntA("MapOverlay","Version",0,settings_path)<SETTINGS_VERSION;
}

// A toggle needs a rest period: the RE0 HD mod's live log showed one press arriving three times 200 ms apart.
// Auto: SD when Classic REbirth runs without HD textures. RE2 has no HDTextures key (REbirth 1.0.9 knows RetroMode and LowResEnable);
// the HD textures come from bio2hd.asi (hires\ hash replacement), so SD = RetroMode or LowResEnable on, or bio2hd.asi not loaded.
static int sd_decide(void){
 if(sd_mode<0){
  int retro=GetPrivateProfileIntA("DLL","RetroMode",0,config_path)!=0,low=GetPrivateProfileIntA("DLL","LowResEnable",0,config_path)!=0;
  int hd=GetModuleHandleA("bio2hd.asi")!=0;
  sd_mode=display_mode==2||(display_mode==0&&(retro||low||!hd));
  log_line(sd_mode?"SD mode: 1x markers and names (DisplayMode=%d retro=%d lowres=%d bio2hd=%d)\n":"HD mode (DisplayMode=%d retro=%d lowres=%d bio2hd=%d)\n",display_mode,retro,low,hd);
 }
 return sd_mode;
}
#define DEBOUNCE_MS 350
static int debounced(unsigned bit){
 static LARGE_INTEGER last[17];LARGE_INTEGER now={0},rate={0};
 QueryPerformanceFrequency(&rate);if(!rate.QuadPart)return 0; // no counter: no rest period
 QueryPerformanceCounter(&now);
 unsigned k=0;while(k<16&&!(bit>>k&1))k++;
 if(last[k].QuadPart&&(now.QuadPart-last[k].QuadPart)*1000<rate.QuadPart*DEBOUNCE_MS)return 1; // no 64-bit division (-nostdlib)
 last[k]=now;return 0;
}
#define KEY_MOD 2048 /* Shift, or Ctrl with Modifier=Ctrl */
static void update_toggle(unsigned mode,int down){
 unsigned pressed=(unsigned)down&~toggle_was_down&~KEY_MOD;
 toggle_was_down=(unsigned)down;
 if(mode!=0)return;
 for(unsigned bit=1;bit<0x40000;bit<<=1)if(pressed&bit&&debounced(bit))pressed&=~bit;
 if(pressed&1)overlay_enabled=!overlay_enabled;
 if(pressed&2)room_names_enabled=!room_names_enabled;
 if(pressed&4)locks_enabled=!locks_enabled;
 if(pressed&8)items_enabled=!items_enabled;
 if(pressed&16)documents_enabled=!documents_enabled;
 if(pressed&32)english_enabled=!english_enabled;
 if(pressed&64)puzzles_enabled=!puzzles_enabled;
 if(pressed&128)common_enabled=!common_enabled;
 if(pressed&256)monsters_enabled=!monsters_enabled;
 if(pressed&131072)events_enabled=!events_enabled;
 if(pressed&4096)scope=scope%3+1;
 if(pressed&8192)legend_enabled=!legend_enabled;
 if(!sd_on()&&pressed&16384)item_names_enabled=item_names_enabled==NAMES_ALL?NAMES_NO_COMMON:item_names_enabled==NAMES_NO_COMMON?NAMES_OFF:NAMES_ALL; // all -> no common -> off -> all
 // RE0 keys: - · + name size, [ · ] name opacity; with the modifier, icon size and icon opacity.
 int up=pressed&512?10:pressed&1024?-10:0,fade=pressed&65536?10:pressed&32768?-10:0;
 if(sd_on());else if(down&KEY_MOD){icon_size=icon_size_value((int)icon_size+up);icon_opacity=opacity_value((int)icon_opacity+fade);}
 else{name_size=size_value((int)name_size+up);name_opacity=opacity_value((int)name_opacity+fade);}
 if(pressed)save_settings();
}

static void (__cdecl *map_draw)(void);
static int (__cdecl *flat_rect)(void*,int,int);
static int (__cdecl *check_bit)(void*,unsigned);
static uintptr_t addr(unsigned va){return (uintptr_t)game+va-0x400000;}
static unsigned sd_textures[SD_PAGES];
static unsigned texture,room_textures_ko[ROOM_LABEL_PAGE_COUNT_KO],room_textures_en[ROOM_LABEL_PAGE_COUNT_EN];
static unsigned item_textures_ko[ITEM_LABEL_PAGE_COUNT_KO],item_textures_en[ITEM_LABEL_PAGE_COUNT_EN],icon_texture,key_art_texture;
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
  for(unsigned i=0;i<SD_PAGES;i++)sd_textures[i]=0;
  icon_texture=key_art_texture=rank_texture=nav_texture=0;for(unsigned i=0;i<FILL_MASK_FLOORS;i++)fill_textures[i]=0;
  texture_device=device;resident_english=english_enabled;
 }
 if(resident_english!=english_enabled){
  // Native handle/work pools (0x416c40/0x416b50) are shared with the game and ran dry after ~68 handles with both
  // languages resident, leaving English legend row 2 (pages 10-11) blank (user 2026-10-26). Keep one language only.
  void (__thiscall *release)(void*,unsigned)=(void*)addr(0x416be0);
  unsigned *rooms=resident_english?room_textures_en:room_textures_ko,*items=resident_english?item_textures_en:item_textures_ko;
  unsigned nr=resident_english?ROOM_LABEL_PAGE_COUNT_EN:ROOM_LABEL_PAGE_COUNT_KO,ni=resident_english?ITEM_LABEL_PAGE_COUNT_EN:ITEM_LABEL_PAGE_COUNT_KO;
  for(unsigned i=0;i<SD_PAGES;i++)if(sd_page_lang[i]==(resident_english?1u:2u)&&sd_textures[i]){release(marni,sd_textures[i]);sd_textures[i]=0;}
  for(unsigned i=0;i<nr;i++)if(rooms[i]){release(marni,rooms[i]);rooms[i]=0;}
  for(unsigned i=0;i<ni;i++)if(items[i]){release(marni,items[i]);items[i]=0;}
  resident_english=english_enabled;
 }
 if(!*cache){*cache=create_texture(pixels);if(*cache||frames%120==1)log_line("atlas texture=%u device=%08lx\n",*cache,(unsigned long)device);}
 return *cache;
}
static unsigned sd_texture(unsigned page){return cached_texture(sd_textures+page,sd_pixels[page]);}
static unsigned get_texture(void){return sd_on()?sd_texture(0):cached_texture(&texture,atlas_pixels);}
static unsigned icon_tex(void){return sd_on()?sd_texture(0):cached_texture(&icon_texture,overlay_icon_pixels);}
typedef struct {short x,y,w,h;} Bounds;
static Bounds occupied[512]; // police 1F draws ~200 quads; a full list keeps label placement exact
static unsigned occupied_count;
// Each box carries the weight names pay for covering it (RE0 HD map mod): stars, diamonds, panels and key names 8,
// room names 4, other names 2, other markers 1.
static unsigned char occupied_w[512],reserve_weight=1;
static void reserve(int x,int y,int w,int h){if(occupied_count<sizeof(occupied)/sizeof(occupied[0])){occupied_w[occupied_count]=reserve_weight;occupied[occupied_count++]=(Bounds){x,y,w,h};}}
static void quad_draw(int x,int y,int w,int h,unsigned u,unsigned v,unsigned sw,unsigned sh,unsigned tex){
 uintptr_t next=*(uintptr_t*)addr(0x524e1c),end=*(uintptr_t*)addr(0x524e20);
 if(!tex||w<1||h<1||next>end||end-next<32+8192)return;
 if(zoom_on){ // the map runs past the screen: crop instead of pushing markers onto the edge
  int l=x<1?1-x:0,r=x+w>318?x+w-318:0,t=y<1?1-y:0,b=y+h>238?y+h-238:0;
  if(l+r>=w||t+b>=h)return;
  u+=sw*l/w;v+=sh*t/h;sw-=sw*(l+r)/w;sh-=sh*(t+b)/h;if(!sw)sw=1;if(!sh)sh=1;
  x+=l;y+=t;w-=l+r;h-=t+b;
 }
 if(w>317||h>237)return;
 if(x<1)x=1;if(x+w>318)x=318-w;
 if(y<1)y=1;if(y+h>238)y=238-h;
 if(quad_mode==1){reserve(x,y,w,h);return;}
 unsigned char *p=(unsigned char*)next;
 for(unsigned j=0;j<32;j++)p[j]=0;
 *(unsigned*)(p+4)=0x24;*(unsigned*)(p+8)=tex;
 if(quad_color){*(unsigned*)(p+4)=0x400025;*(unsigned*)(p+28)=quad_color;}
 else if(!sd_on()&&(drawing_names?name_opacity<100:drawing_icons&&icon_opacity<100)){
  // Native coloured-texture packet: alpha in byte31; SRCALPHA/INVSRCALPHA, RGB555 texture unchanged.
  *(unsigned*)(p+4)=0x400025;*(unsigned*)(p+28)=(((drawing_names?name_opacity:icon_opacity)*255+50)/100<<24)|0x808080;
 }
 *(short*)(p+16)=x;*(short*)(p+18)=y;
 *(short*)(p+20)=x+w-1;*(short*)(p+22)=y+h-1;
 p[24]=u;p[25]=v;p[26]=u+sw-1;p[27]=v+sh-1;
 void (__thiscall *queue)(void*,void*,unsigned)=(void*)addr(0x4021c0);
 // Native key-marker priority keeps additions underneath map transition fades.
 queue(*(void**)addr(0x6805b8),p,6);
 *(uintptr_t*)addr(0x524e1c)=next+32;
 if(quad_mode!=2)reserve(x,y,w,h);
}
// Lock icons share one visible size: atlas rects are cropped to their art, longest side 7.5 px (user 2026-10-27:
// the Lockpick looked larger than the suit keys when every rect was stretched to 12 px wide).
#define LOCK_ICON_TENTHS 75
static void icon_box(int px,int py,const Icon *i,int *x,int *y,int *w,int *h){
 int m=i->w>i->h?i->w:i->h;
 *w=(i->w*LOCK_ICON_TENTHS*(int)icon_size*zoom_gain()/10000+m*5)/(m*10);*h=(i->h*LOCK_ICON_TENTHS*(int)icon_size*zoom_gain()/10000+m*5)/(m*10);
 if(sd_on())*w=*h=9;
 if(*w<1)*w=1;if(*h<1)*h=1;
 *x=px-*w/2;*y=py-*h/2;
 if(zoom_on)return;
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
  if(r->w<=isz(8)&&r->h<=isz(8)&&r->x<=cx&&cx<r->x+r->w&&r->y<=cy&&cy<r->y+r->h)continue;
  if(x<r->x+r->w&&r->x<x+w&&y<r->y+r->h&&r->y<y+h)return 1;
 }
 return 0;
}
// A star/diamond-sized box among occupied[0..n) containing (cx,cy).
static int on_marker(unsigned n,int cx,int cy){
 for(unsigned j=0;j<n;j++){
  const Bounds *r=occupied+j;
  if(r->w<=isz(8)&&r->h<=isz(8)&&r->x<=cx&&cx<r->x+r->w&&r->y<=cy&&cy<r->y+r->h)return 1;
 }
 return 0;
}
// Weighted overlap of a w x h box at (x,y), counting boxes of weight >= min_w only.
static int overlap_score(int x,int y,int w,int h,unsigned min_w){
 int score=0;
 for(unsigned j=0;j<occupied_count;j++){
  Bounds *r=occupied+j;
  if(occupied_w[j]<min_w)continue;
  int l=x>r->x?x:r->x,t=y>r->y?y:r->y;
  int right=x+w<r->x+r->w?x+w:r->x+r->w,bottom=y+h<r->y+r->h?y+h:r->y+r->h;
  if(right>l&&bottom>t)score+=(right-l)*(bottom-t)*occupied_w[j];
 }
 return score;
}
// Marker names (RE0 HD map mod rule): touching the marker box (mx,my,mw,mh) right, left, below, above, then the four
// corners; the first spot with no overlap wins, else the least overlap, and only if that still overlaps a second ring
// one name height further out. A wrapped name (l2) draws its lines toward the marker: left-aligned on the right, right-
// aligned on the left, centred above/below. strict (common items): only a spot overlapping nothing of weight >= 2, else
// no name. Returns whether the name was drawn.
// slide (marker names, not key names): when none of the eight touching spots is free, the name slides along the marker's
// edge, still touching it, to the first position that overlaps nothing; the second ring is used only after that, and never
// by strict names (documents, common items), which are dropped instead of floating a name height away or sitting under an
// icon. At 2x zoom the eight spots are crowded, and a two-line document name used to land 15 px from its icon (user 2026-11-09).
static int item_label_draw(int mx,int my,int mw,int mh,const ItemLabel *l,unsigned tex,const ItemLabel *l2,unsigned tex2,int strict,int slide){
 int w1=name_dimension(l->w),h1=name_dimension(l->h),w2=l2?name_dimension(l2->w):0,h2=l2?name_dimension(l2->h):0;
 int w=w1>w2?w1:w2,h=h1+h2,bx=1,by=1,side=0,best=0x7fffffff;
 const signed char spot[8][3]={{1,0,-1},{-1,0,1},{0,1,0},{0,-1,0},{1,1,-1},{1,-1,-1},{-1,1,1},{-1,-1,1}}; // x side, y side, alignment
 for(int ring=0;slide&&ring<1&&best;ring++)for(unsigned c=0;c<8&&best;c++){ // a free touching spot, fixed then sliding
  int sx=spot[c][0],sy=spot[c][1];
  int x=sx>0?mx+mw:sx<0?mx-w:mx+mw/2-w/2,y=sy>0?my+mh:sy<0?my-h:my+mh/2-h/2;
  if(x<1)x=1;if(x+w>318)x=318-w;if(y<1)y=1;if(y+h>238)y=238-h;
  if(!overlap_score(x,y,w,h,1)){best=0;bx=x;by=y;side=spot[c][2];}
 }
 for(int k=1;slide&&best&&k<=mw+mh+w+h;k++)for(int dir=-1;dir<=1&&best;dir+=2)for(unsigned c=0;c<4&&best;c++){
  // c: right, left, below, above; the offset k runs along the edge, nearest the centre first.
  int x,y,sd=c<2?(c?1:-1):0;
  if(c<2){x=c?mx-w:mx+mw;y=my+mh/2-h/2+dir*k;if(y<=my-h||y>=my+mh)continue;}
  else{y=c==2?my+mh:my-h;x=mx+mw/2-w/2+dir*k;if(x<=mx-w||x>=mx+mw)continue;}
  if(x<1||x+w>318||y<1||y+h>238)continue;
  if(!overlap_score(x,y,w,h,1)){best=0;bx=x;by=y;side=sd;}
 }
 for(int ring=0;ring<(strict&&slide?0:2)&&best;ring++)for(unsigned c=0;c<8;c++){
  int sx=spot[c][0],sy=spot[c][1];
  int x=sx>0?mx+mw+ring*h:sx<0?mx-w-ring*h:mx+mw/2-w/2;
  int y=sy>0?my+mh+ring*h:sy<0?my-h-ring*h:my+mh/2-h/2;
  if(x<1)x=1;if(x+w>318)x=318-w;
  if(y<1)y=1;if(y+h>238)y=238-h;
  if(strict&&overlap_score(x,y,w,h,2))continue;
  int score=overlap_score(x,y,w,h,1);
  if(score<best){best=score;bx=x;by=y;side=spot[c][2];}
  if(!score)break;
 }
 if(best==0x7fffffff)return 0;
 drawing_names=1;
 quad_draw(bx+(side<0?0:side>0?w-w1:(w-w1)/2),by,w1,h1,l->u,l->v,l->w,l->h,tex);
 if(l2)quad_draw(bx+(side<0?0:side>0?w-w2:(w-w2)/2),by+h1,w2,h2,l2->u,l2->v,l2->w,l2->h,tex2);
 drawing_names=0;
 return 1;
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
// Folded legend: one hint line on its bottom row (label 24). The rank line is its own setting.
#define LEGEND_HINT_Y (LEGEND_Y+18)
#define HELP_ZOOM 22 /* +zoom_on */
#define HELP_FOLDED 24
#define HELP_HIDE 25
#define HELP_ITEM_NAMES 26 /* all; 27 off; the no-common label is appended after the percentages */
#define HELP_ITEM_NAMES_NO_COMMON 54
#define HELP_EVENTS 55 /* ON; 56 OFF */
#define HELP_LANGUAGE 13 /* +1 when English */
static unsigned help_item_names(void){return item_names_enabled==NAMES_NO_COMMON?HELP_ITEM_NAMES_NO_COMMON:HELP_ITEM_NAMES+(item_names_enabled==NAMES_OFF);}
#define HELP_READOUT 28 /* name opacity, name size, Shift +, Ctrl +, icon opacity, icon size */
#define HELP_PERCENT 34 /* 10%..200% */
static const RoomLabel *help_label(unsigned id){return active_room_labels()+active_help_start()+id;}
static int help_w(unsigned id){unsigned s=english_enabled?ROOM_LABEL_SCALE_EN:ROOM_LABEL_SCALE_KO;return (int)(help_label(id)->w+s/2)/(int)s;}
static int help_h(unsigned id){unsigned s=english_enabled?ROOM_LABEL_SCALE_EN:ROOM_LABEL_SCALE_KO;return (int)(help_label(id)->h+s/2)/(int)s;}
static int help_draw_mode; // 0 measure only (help_layout fills the panel boxes), 1 draw
static int help_put(unsigned id,int x,int y){
 const RoomLabel *l=help_label(id);int w=help_w(id),h=help_h(id);
 if(help_draw_mode){unsigned tex=cached_texture(active_room_cache(l->page),active_room_pixels(l->page));if(tex)room_label_draw(x+w/2,y+h/2,l->u,l->v,l->w,l->h,tex);}
 return w;
}
// Panels: the legend (or its folded hint) and the readout. Names steer around them; a marker touching one is not drawn.
static Bounds panels[2];static unsigned panel_count;
static int in_panel(int x,int y,int w,int h){
 for(unsigned j=0;j<panel_count;j++){const Bounds *r=panels+j;if(x<r->x+r->w&&r->x<x+w&&y<r->y+r->h&&r->y<y+h)return 1;}
 return 0;
}
// Readout (the RE0 HD map mod's value panel): a name column (opacity over size) and an icon column (modifier + opacity
// over size), each value after its hint (user 2026-11-07: same kind stacked). Top left, above the native area title: no
// RE2 map row reaches it, while the bottom right held 54 marker rows (4 key items); the rank line (top right, <= 142 px)
// stays clear. ROOM_READOUT_W is generate_room_names.readout_width, which reserves this box for room names.
#include "sd_draw.h"
#define READOUT_X 8
#define READOUT_Y 1
static void readout_layout(void){
 const int width=english_enabled?ROOM_READOUT_W_EN:ROOM_READOUT_W_KO,x0=READOUT_X,y0=READOUT_Y;
 int value=0;
 for(unsigned i=0;i<20;i++)if(help_w(HELP_PERCENT+i)>value)value=help_w(HELP_PERCENT+i);
 const unsigned values[4]={name_opacity,name_size,icon_opacity,icon_size};
 int name_hint=help_w(HELP_READOUT)>help_w(HELP_READOUT+1)?help_w(HELP_READOUT):help_w(HELP_READOUT+1);
 int icon_hint=help_w(HELP_READOUT+4)>help_w(HELP_READOUT+5)?help_w(HELP_READOUT+4):help_w(HELP_READOUT+5);
 int icon_x=x0+name_hint+2+value+6,hint_x=icon_x+help_w(HELP_READOUT+2+(unsigned)modifier_ctrl)+2;
 for(unsigned r=0;r<2;r++){ // r 0 opacity, 1 size; values line up within each column
  int y=y0+(int)r*8;
  help_put(HELP_READOUT+r,x0,y);help_put(HELP_PERCENT+values[r]/10-1,x0+name_hint+2,y);
  help_put(HELP_READOUT+2+(unsigned)modifier_ctrl,icon_x,y);
  help_put(HELP_READOUT+4+r,hint_x,y);help_put(HELP_PERCENT+values[2+r]/10-1,hint_x+icon_hint+2,y);
 }
 panels[panel_count++]=(Bounds){x0,y0,width,16};
}
// Native floor arrows (cursor texture, v >= 24) are drawn at x 152..165, y 214..225: the legend column after [2]/[7]
// starts past them in both languages.
#define ARROW_LANE_END 166
static void legend_layout(void){
 if(sd_on()){sd_legend_draw();return;}
 panel_count=0;
 if(!legend_enabled){ // folded: one hint line, no readout
  int w=help_put(HELP_FOLDED,8,LEGEND_HINT_Y);panels[panel_count++]=(Bounds){8,LEGEND_HINT_Y,w,help_h(HELP_FOLDED)};
  return;
 }
 // 2 rows x 6 columns: [0]..[4] / [5]..[9], then [H] names over [Action] zoom (user 2026-11-07).
 const unsigned state[12]={overlay_enabled?1:2,room_names_enabled?3:4,locks_enabled?5:6,
                          items_enabled?7:8,documents_enabled?9:10,help_item_names(),
                          puzzles_enabled?11:12,events_enabled?HELP_EVENTS:HELP_EVENTS+1,common_enabled?17:18,monsters_enabled?15:16,18+scope,
                          HELP_ZOOM+(unsigned)zoom_on};
 int col_width[LEGEND_COLUMNS]={0},x[LEGEND_COLUMNS]={8};
 for(unsigned n=0;n<12;n++){if(n==5)continue;int w=help_w(state[n]);if(w>col_width[n%6])col_width[n%6]=w;} // n 5 is the [H] state: it sits in the header line
 for(unsigned col=1;col<LEGEND_COLUMNS;col++){
  x[col]=x[col-1]+col_width[col-1]+4;
  if(col==3&&x[col]<ARROW_LANE_END)x[col]=ARROW_LANE_END;
 }
 // Header line: title, then [~] hide first.
 int hx=x[0]+help_put(0,x[0],LEGEND_Y)+6;
 hx+=help_put(HELP_HIDE,hx,LEGEND_Y)+8;
 hx+=help_put(state[5],hx,LEGEND_Y)+8; // [H] item names: all / no common / off (too wide for the grid's sixth column)
 unsigned language=HELP_LANGUAGE+(unsigned)english_enabled;
 int header_end=318;help_put(language,header_end-help_w(language),LEGEND_Y); // [\\] language next to it (user 2026-11-08)
 for(unsigned n=0;n<12;n++)if(n!=5)help_put(state[n],x[n%6],LEGEND_Y+10+(int)(n/6)*8);
 {int right=x[5]+col_width[5]-1,header_right=header_end-1;panels[panel_count++]=(Bounds){1,LEGEND_Y,right>header_right?right:header_right,238-LEGEND_Y};}
 readout_layout();
}
static void help_draw(void){help_draw_mode=1;legend_layout();help_draw_mode=0;if(!sd_on())rank_draw();}
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
 int cx=MX(r->x),cy=MY(r->y);
 if(r->lx0|r->ly0|r->lx1|r->ly1){cx=MX(r->lx1)+(r->x-r->lx1)*(int)name_size*4/500;cy=MY(r->ly1)+(r->y-r->ly1)*(int)name_size*4/500;}
 *w=name_dimension(l->w);*h=name_dimension(l->h);*x=cx-*w/2;*y=cy-*h/2;
}
static const Icon *door_icon(const Door *d,unsigned pl,unsigned mpl,unsigned floor,unsigned flags){
 if(d->pl!=mpl||d->floor!=floor)return 0;
 if((d->key==93&&(flags&0x40000000))||
    ((d->key==94||d->key==95||d->key==98||d->key==99)&&!(flags&0x40000000)))return 0;
 if(!(flags&0x40000000)){if(d->scenario_mask&64)return 0;}
 else {if(pl&&(d->scenario_mask&64))return 0;if(d->scenario_mask&128)return 0;}
 if(!room_shown(pl,floor,d->seen))return 0;
 if(d->bank==255?check_bit((void*)addr(0x98ed2c),d->unlock):bank_bit(d->bank,d->unlock))return 0;
 if(sd_on()){ // approved SD lock table (sd_icons.py LOCKS): one 9x9 padlock per key
  static Icon sd_lock;
  if(d->key>=100||sd_lock_sprite[d->key]==0xFFFF)return 0;
  const SdSprite *s=sd_sprites+sd_lock_sprite[d->key];sd_lock=(Icon){d->key,s->u,s->v,s->w,s->h};return &sd_lock;
 }
 for(unsigned k=0;k<sizeof(icons)/sizeof(icons[0]);k++)if(icons[k].item==d->key)return icons+k;
 return 0;
}
// LockSide=1 (default since 1.4, RE1 HD map mod style): the lock sits beside the door in the room not entered yet: its own room when only the
// destination was visited, else the destination (x2,y2, the door's arrival point a few px past it). LockSide=0 and doors without a drawn other
// side (seen2=255, e.g. doors to another floor): on the door. HD and SD share this position.
// Centre of the room whose seen bit is `seen` on this floor (native room table: x,y at +4/+6, w,h at +2/+3, seen at +0xc).
static int room_centre(unsigned pl,unsigned floor,unsigned seen,int *cx,int *cy){
 if(floor>=20)return 0;
 const unsigned char *f=(const unsigned char*)addr(pl?0x53eb98:0x53eaf8)+floor*8,*e=(const unsigned char*)addr(*(const uint32_t*)f);
 for(unsigned k=0;k<f[4];k++,e+=16)if(e[0xc]==seen){*cx=*(const short*)(e+4)+e[2]/2;*cy=*(const short*)(e+6)+e[3]/2;return 1;}
 return 0;
}
// Lock marker centre. LockSide=0, doors without a drawn other side (seen2=255, no native bar): on the door spot. LockSide=1: beside the
// native door bar (an 8x8 sprite at the door's x,y; the marker box would sit under it, user 2026-11-13: "not beside the door, so hidden"),
// on the side of the room not entered yet: out from the bar's centre along the axis towards that room's centre, just clear of the bar
// (half the bar + half the marker + 1 px; the bar doubles at 2x zoom, the marker stays 1:1 in SD).
static void door_pos(const Door *d,const Icon *i,int dx,int dy,int *x,int *y){
 int at=lock_side&&d->seen2!=255?(check_bit((void*)addr(0x98ec04),d->seen2)&&!check_bit((void*)addr(0x98ec04),d->seen)?1:2):0;
 if(!at){*x=MX(d->x);*y=MY(d->y);return;}
 int rx,ry,bx,by,bw,bh,z=zoom_on?2:1,cx=d->x+4,cy=d->y+4;
 if(!room_centre(d->pl&1,d->floor,at==1?d->seen:d->seen2,&rx,&ry)){rx=at==1?d->x1:d->x2;ry=at==1?d->y1:d->y2;} // fallback: the door AOT points
 icon_box(0,0,i,&bx,&by,&bw,&bh);
 int vx=rx-cx,vy=ry-cy,horizontal=(vx<0?-vx:vx)>=(vy<0?-vy:vy);
 int off=4*z+(horizontal?bw:bh)/2+1;
 *x=MX(cx)+(horizontal?(vx<0?-off:off):0);*y=MY(cy)+(horizontal?0:(vy<0?-off:off));
}
// Name categories (ItemLabel.cat, tools/mapgen/category_colors.py): each is drawn in its legend row's colour.
enum { LABEL_KEY,LABEL_LOCK,LABEL_PUZZLE,LABEL_DOCUMENT,LABEL_COMMON };
static const ItemLabel *key_label(unsigned item,unsigned cat){
 const ItemLabel *labels=active_item_labels();
 for(unsigned k=0;k<active_item_count();k++)if(labels[k].item==item&&labels[k].cat==cat)return labels+k;
 return 0;
}
// A wrapped name's second line: the next row of the same item and category.
static const ItemLabel *second_line(const ItemLabel *l){
 return l+1<active_item_labels()+active_item_count()&&l[1].item==l->item&&l[1].cat==l->cat?l+1:0;
}
// Only key items with a name get a star, as before.
static int key_item_shown(const MapItem *i,unsigned pl,unsigned mpl,unsigned floor){
 return key_label(i->item,LABEL_KEY)&&item_enabled(i->item)&&!map_item(i->item)&&!common_item(i->item)&&i->pl==mpl&&i->floor==floor&&
        room_shown(pl,floor,i->seen)&&!bank_bit(i->bank,i->bit)&&guards_pass(map_item_guards+i->guard_start,i->guard_count);
}
// Key-item art (2026-11-08): the 37 sprites of key_art.h plus the lock-icon sprites of atlas.h. The longest side fills the
// marker box and the aspect is kept (a shotgun is a thin strip, not a square), at least 2 px thick so it never vanishes;
// the name then touches the drawn art, not the empty square around it.
static int key_art_ref(unsigned item,unsigned *tex,int *u,int *v,int *w,int *h){
 if(sd_on())return 0; // SD: every key item is the cyan circle
 for(unsigned q=0;q<sizeof(key_art)/sizeof(key_art[0]);q++)if(key_art[q].item==item){
  *tex=cached_texture(&key_art_texture,key_art_pixels);*u=key_art[q].u;*v=key_art[q].v;*w=key_art[q].w;*h=key_art[q].h;return 1;}
 for(unsigned q=0;q<sizeof(icons)/sizeof(icons[0]);q++)if(icons[q].item==item){
  *tex=get_texture();*u=icons[q].u;*v=icons[q].v;*w=icons[q].w;*h=icons[q].h;return 1;}
 return 0;
}
static void art_fit(int x,int y,int sw,int aw,int ah,int *ox,int *oy,int *ow,int *oh){
 int m=aw>ah?aw:ah,min=sw>=4?2:1,w=(sw*aw+m/2)/m,h=(sw*ah+m/2)/m;
 if(w<min)w=min;if(h<min)h=min;
 *ow=w;*oh=h;*ox=x+(sw-w)/2;*oy=y+(sw-h)/2;
}
// Marker centre and width; a combined puzzle/key marker sits on its puzzle and the name follows it.
static int key_marker(const MapItem *i,int dx,int dy,int *px,int *py){
 const MapInteraction *pz=combo_of(i);
 if(pz){*px=MX(pz->x+PROJ_CENTRE);*py=MY(pz->y+PROJ_CENTRE);return isz(PUZZLE_KEY_W);}
 *px=MX(i->x+PROJ_CENTRE);*py=MY(i->y+PROJ_CENTRE);
 return isz((OVERLAY_ICON_TEX/OVERLAY_ICON_SCALE*90+50)/100); // standalone key-item star stays at 90% icon size
}
// Drawn marker box, clamped to the map like the star itself.
static int key_box(const MapItem *i,int dx,int dy,int *x,int *y){
 int px,py,sw=key_marker(i,dx,dy,&px,&py);
 *x=px-sw/2;*y=py-sw/2;
 if(zoom_on)return sw;
 if(*x<1)*x=1;if(*x>318-sw)*x=318-sw;
 if(*y<1)*y=1;if(*y>238-sw)*y=238-sw;
 return sw;
}
static int document_shown(const MapDocument *m,unsigned pl,unsigned mpl,unsigned floor){
 return m->pl==mpl&&m->floor==floor&&room_shown(pl,floor,m->seen)&&!bank_bit(m->bank,m->bit)&&
        guards_pass(document_guards+m->guard_start,m->guard_count);
}
// [6] events: story scenes (FMV), a purple '?' diamond at the scene's trigger until its progress flag is set.
static int puzzle_drawn(const MapInteraction *m,unsigned pl,unsigned mpl,unsigned floor){
 return puzzles_enabled&&m->pl==mpl&&m->floor==floor&&m->kind==6&&room_shown(pl,floor,m->seen)&&
        guards_pass(interaction_guards+m->guard_start,m->guard_count)&&!puzzle_replaced(m);
}
// High priority first (user 2026-10-26): the native queue (0x416500) pushes onto a list head, so earlier quads draw on
// top. Order: key stars, key names, puzzle diamonds, then (draw_names) room names and low-priority icons; key items are
// never covered, common items and monsters always are. Names ignore those low-priority icons, avoid key and
// puzzle markers, and only lean away from room names, which place themselves afterwards around the names.
// [6] events (2026-11-10): one marker per floor, the next pending scene. Story order is the ascending FG_COMMON done flag (the
// flags are handed out in play order); a scene whose flag is set is done and the next one appears. The marker is drawn here,
// right after the key stars, so key names steer around it, and it slides to a free spot if a star sits on it.
static const MapInteraction *next_event(unsigned mpl,unsigned floor){
 const MapInteraction *best=0;unsigned best_bit=0x10000;
 for(unsigned j=0;events_enabled&&j<sizeof(map_interactions)/sizeof(map_interactions[0]);j++){
  const MapInteraction *m=map_interactions+j;
  if(m->pl!=mpl||m->floor!=floor||m->kind!=EVENT_KIND||!guards_pass(interaction_guards+m->guard_start,m->guard_count))continue;
  unsigned bit=interaction_guards[m->guard_start+m->guard_count-1].bit; // the done flag is the last guard
  if(bit<best_bit){best_bit=bit;best=m;}
 }
 return best;
}
static void draw_event(unsigned pl,unsigned mpl,unsigned floor,int dx,int dy,unsigned st){
 const MapInteraction *m=next_event(mpl,floor);
 if(!m||!room_shown(pl,floor,m->seen))return; // the next pending scene's room is not revealed yet: no marker
 for(unsigned k=0;k<sizeof(overlay_icons)/sizeof(overlay_icons[0]);k++)if(overlay_icons[k].kind==16){
  const OverlayIcon *i=overlay_icons+k;
  int d=isz(6),cx=MX(m->x+PROJ_CENTRE)-d/2,cy=MY(m->y+PROJ_CENTRE)-d/2,bx=cx,by=cy;
  const signed char off[9][2]={{0,0},{1,0},{-1,0},{0,1},{0,-1},{1,1},{1,-1},{-1,1},{-1,-1}};
  for(unsigned c=0;c<9;c++){
   int x=cx+off[c][0]*d,y=cy+off[c][1]*d;
   if(in_panel(x,y,d,d))continue;
   if(!overlap_score(x,y,d,d,1)){bx=x;by=y;break;}
  }
  if(zoom_on&&(bx+d<1||bx>318||by+d<1||by>238))return;
  if(!in_panel(bx,by,d,d))icon_quad(16,bx,by,d,i,st);
  return;
 }
}
static void name_marker(int x,int y,int w,int h,unsigned item,unsigned tier);
static unsigned draw_key_items(unsigned pl,unsigned mpl,unsigned floor,int dx,int dy){
 unsigned n=0,st=icon_tex();
 high_count=0;
 if(!overlay_enabled||!st)return 0;
 reserve_weight=8; // stars, diamond stand-ins, panels
 for(unsigned j=0;j<sizeof(map_items)/sizeof(map_items[0]);j++){
  const MapItem *i=map_items+j;if(!key_item_shown(i,pl,mpl,floor))continue;
  int x,y,sw=key_box(i,dx,dy,&x,&y),kind=combo_of(i)?15:14;
  if(in_panel(x,y,sw,sw))continue; // under the legend or readout: neither star nor name
  unsigned at;int au,av,aw,ah;
  if(key_art_ref(i->item,&at,&au,&av,&aw,&ah)){
   int fx,fy,fw,fh;art_fit(x,y,sw,aw,ah,&fx,&fy,&fw,&fh);
   quad_draw(fx,fy,fw,fh,au,av,aw,ah,at);continue;
  }
  for(unsigned q=0;q<sizeof(overlay_icons)/sizeof(overlay_icons[0]);q++)if(overlay_icons[q].kind==kind){
   icon_quad(kind,x,y,sw,overlay_icons+q,st);break;}
 }

 draw_event(pl,mpl,floor,dx,dy,st);
 for(unsigned j=0;j<sizeof(map_interactions)/sizeof(map_interactions[0]);j++){
  const MapInteraction *m=map_interactions+j;
  if(puzzle_drawn(m,pl,mpl,floor))reserve(MX(m->x+PROJ_CENTRE)-isz(6)/2,MY(m->y+PROJ_CENTRE)-isz(6)/2,isz(6),isz(6));
 }
 // Stand-ins the names steer around and then drop: legend, locks, files/area maps, save/item-box markers, room names.
 unsigned rooms=occupied_count,flags=*(uint32_t*)addr(0x989ed0);
 for(unsigned j=0;j<panel_count;j++)reserve(panels[j].x,panels[j].y,panels[j].w,panels[j].h); // opaque text would cover a name
 reserve_weight=1;
 for(unsigned j=0;locks_enabled&&j<sizeof(doors)/sizeof(doors[0]);j++){
  const Icon *i=door_icon(doors+j,pl,mpl,floor,flags);
  if(!i)continue;
  int x,y,w,h,cx,cy;door_pos(doors+j,i,dx,dy,&cx,&cy);icon_box(cx,cy,i,&x,&y,&w,&h);reserve(x,y,w,h);
  if(on_marker(rooms,cx,cy))reserve(x+MAP_BADGE,y+MAP_BADGE,w,h); // keep the name off its badge too (see draw_names)
 }
 for(unsigned j=0;documents_enabled&&j<sizeof(map_documents)/sizeof(map_documents[0]);j++){
  const MapDocument *m=map_documents+j;if(document_shown(m,pl,mpl,floor))reserve(MX(m->x+PROJ_CENTRE)-isz(8)/2,MY(m->y+PROJ_CENTRE)-isz(8)/2,isz(8),isz(8));
 }
 for(unsigned j=0;room_names_enabled&&j<sizeof(map_markers)/sizeof(map_markers[0]);j++){
  const MapMarker *m=map_markers+j;
  if(m->pl==mpl&&m->floor==floor&&room_shown(pl,floor,m->seen))reserve(MX(m->x+PROJ_CENTRE)-isz(8)/2,MY(m->y+PROJ_CENTRE)-isz(8)/2,isz(8),isz(8));
 }
 reserve_weight=4;
 for(unsigned j=0;!sd_on()&&room_names_enabled&&j<active_room_count();j++){
  const RoomName *r=active_room_names()+j;
  if(r->pl!=pl||r->floor!=floor||!room_shown(pl,floor,r->seen))continue;
  int x,y,w,h;room_box(r,active_room_labels()+r->label,dx,dy,&x,&y,&w,&h);reserve(x,y,w,h);
 }
 unsigned names=occupied_count;reserve_weight=8;
 for(unsigned j=0;item_names_enabled&&!sd_on()&&j<sizeof(map_items)/sizeof(map_items[0]);j++){
  const MapItem *i=map_items+j;if(!key_item_shown(i,pl,mpl,floor))continue;
  const ItemLabel *l=key_label(i->item,LABEL_KEY),*l2=second_line(l);
  unsigned t=cached_texture(active_item_cache(l->page),active_item_pixels(l->page));
  unsigned t2=l2?cached_texture(active_item_cache(l2->page),active_item_pixels(l2->page)):0;
  int x,y,sw=key_box(i,dx,dy,&x,&y);
  if(in_panel(x,y,sw,sw))continue;
  if(zoom_on&&(x+sw<1||x>318||y+sw<1||y>238))continue; // the name would be pulled back on screen, away from its star
  unsigned at;int au,av,aw,ah,fx=x,fy=y,fw=sw,fh=sw;
  if(key_art_ref(i->item,&at,&au,&av,&aw,&ah))art_fit(x,y,sw,aw,ah,&fx,&fy,&fw,&fh);
  if(t&&(!l2||t2)&&item_label_draw(fx,fy,fw,fh,l,t,l2,t2,0,0))n++;
 }
 // Drop the room-name stand-ins; the real room names are placed later and avoid the key-item names.
 for(unsigned j=names;j<occupied_count;j++){occupied[rooms+j-names]=occupied[j];occupied_w[rooms+j-names]=occupied_w[j];}
 occupied_count-=names-rooms;
 // Diamonds after the names. Names steer around them; where a name still overlaps one, the key item wins and that
 // diamond is skipped (translucent names cannot be drawn over it; user 2026-10-26).
 unsigned name_end=occupied_count;
 for(unsigned j=0;j<sizeof(map_interactions)/sizeof(map_interactions[0]);j++){
  const MapInteraction *m=map_interactions+j;if(!puzzle_drawn(m,pl,mpl,floor))continue;
  int d=isz(6),x=MX(m->x+PROJ_CENTRE)-d/2,y=MY(m->y+PROJ_CENTRE)-d/2,hidden=in_panel(x,y,d,d);
  for(unsigned k=rooms;k<name_end;k++){const Bounds *r=occupied+k;if(x<r->x+r->w&&r->x<x+d&&y<r->y+r->h&&r->y<y+d)hidden=1;}
  if(hidden)continue;
  for(unsigned k=0;k<sizeof(overlay_icons)/sizeof(overlay_icons[0]);k++)if(overlay_icons[k].kind==12){
   const OverlayIcon*i=overlay_icons+k;
   icon_quad(12,x,y,d,i,st);if(m->name)name_marker(x,y,d,d,m->name,1);break;
  }
 }
 high_count=occupied_count;reserve_weight=1;
 return n;
}
// Names of the other drawn markers (RE0 HD map mod: [H] names every marker), after every icon is down: locks, then area
// maps, documents and common items; the last two only where they cover nothing of weight >= 2. Puzzle names come from
// data/marker_names.json (one name per mechanism); unresolved puzzles and documents have none.
typedef struct { short x,y,w,h; unsigned char item,tier; } Named; /* tier: 0 lock, 1 puzzle, 2 area map, 3 document, 4 common item */
static Named named[128];static unsigned named_count;
static void name_marker(int x,int y,int w,int h,unsigned item,unsigned tier){
 // Zoomed in, a marker partly or wholly off screen gets no name: it would be clamped onto the screen edge, far from its icon.
 if(zoom_on&&(x<1||y<1||x+w>318||y+h>238))return;
 if(!sd_on()&&item_names_enabled&&!(item_names_enabled==NAMES_NO_COMMON&&tier==4)&&named_count<sizeof(named)/sizeof(named[0]))named[named_count++]=(Named){(short)x,(short)y,(short)w,(short)h,(unsigned char)item,(unsigned char)tier};
}
static void draw_marker_names(void){
 if(!item_names_enabled||sd_on())return;
 reserve_weight=8;for(unsigned j=0;j<panel_count;j++)reserve(panels[j].x,panels[j].y,panels[j].w,panels[j].h);
 reserve_weight=2;
 for(unsigned tier=0;tier<5;tier++)for(unsigned k=0;k<named_count;k++){
  const Named *m=named+k;
  if(m->tier!=tier)continue;
  static const unsigned char cat_of_tier[5]={LABEL_LOCK,LABEL_PUZZLE,LABEL_DOCUMENT,LABEL_DOCUMENT,LABEL_COMMON};
  const ItemLabel *l=key_label(m->item,cat_of_tier[tier]);if(!l)continue;
  const ItemLabel *l2=second_line(l);
  unsigned t=cached_texture(active_item_cache(l->page),active_item_pixels(l->page));
  unsigned t2=l2?cached_texture(active_item_cache(l2->page),active_item_pixels(l2->page)):0;
  if(t&&(!l2||t2))item_label_draw(m->x,m->y,m->w,m->h,l,t,l2,t2,tier>=3,1);
 }
 reserve_weight=1;
}
// Room names sit under every icon and name (user 2026-11-07, RE0 rule): the native queue draws earlier quads on top, so
// they are queued last (mode 2) after a placement pass (mode 1) that reserves the same boxes where the names used to be
// queued, which keeps every other name's placement as it was.
static unsigned draw_room_names(unsigned pl,unsigned floor,int dx,int dy,int mode){
 unsigned names=0;
 if(sd_on())return mode==2?sd_room_names(pl,floor,dx,dy):0; // SD names are fixed (sd_layout.py), nothing to place
 quad_mode=mode;drawing_names=1;reserve_weight=4;
 for(unsigned j=0;overlay_enabled&&room_names_enabled&&j<active_room_count();j++){
  const RoomName *r=active_room_names()+j;
  if(r->pl!=pl||r->floor!=floor||!room_shown(pl,floor,r->seen))continue;
  const RoomLabel *l=active_room_labels()+r->label;
  unsigned t=cached_texture(active_room_cache(l->page),active_room_pixels(l->page));
  if(!t)continue;
  if(r->lx0|r->ly0|r->lx1|r->ly1){ // axis-aligned leader line, opaque texel (0,0)
   int x0=r->lx0<r->lx1?r->lx0:r->lx1,y0=r->ly0<r->ly1?r->ly0:r->ly1;
   int z=zoom_on?2:1;
   quad_draw(MX(x0),MY(y0),(r->lx0>r->lx1?r->lx0-r->lx1:r->lx1-r->lx0)*z+1,(r->ly0>r->ly1?r->ly0-r->ly1:r->ly1-r->ly0)*z+1,0,0,1,1,t);
  }
  int x,y,w,h;room_box(r,l,dx,dy,&x,&y,&w,&h);
  quad_draw(x,y,w,h,l->u,l->v,l->w,l->h,t);names++;
 }
 drawing_names=0;reserve_weight=1;quad_mode=0;
 return names;
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
 legend_layout(); // measure: panel boxes for the names and markers below
 collect_combos(pl,mpl,floor);
 drawing_icons=1;
 named_count=0;pickups=draw_key_items(pl,mpl,floor,dx,dy);
 names=draw_room_names(pl,floor,dx,dy,1); // placement only; queued last, below
 // Typewriter / item-box icons share the room-name toggle and visited-room gate.
 unsigned marks=0,docmarks=0;
 for(unsigned j=0;overlay_enabled&&room_names_enabled&&j<sizeof(map_markers)/sizeof(map_markers[0]);j++){
  const MapMarker *m=map_markers+j;
  if(m->pl!=mpl||m->floor!=floor||!room_shown(pl,floor,m->seen))continue;
  unsigned t=icon_tex();
  if(!t)break;
  for(unsigned k=0;k<sizeof(overlay_icons)/sizeof(overlay_icons[0]);k++)if(overlay_icons[k].kind==m->kind){
   const OverlayIcon *i=overlay_icons+k;int w=isz(OVERLAY_ICON_TEX/OVERLAY_ICON_SCALE);
   // Exact spot, no collision displacement (it pushed icons into neighbouring rooms).
   if(!under_high(MX(m->x+PROJ_CENTRE)-w/2,MY(m->y+PROJ_CENTRE)-w/2,w,w)&&!in_panel(MX(m->x+PROJ_CENTRE)-w/2,MY(m->y+PROJ_CENTRE)-w/2,w,w))icon_quad(m->kind,MX(m->x+PROJ_CENTRE)-w/2,MY(m->y+PROJ_CENTRE)-w/2,w,i,t);marks++;break;
  }
 }
 for(unsigned j=0;overlay_enabled&&documents_enabled&&j<sizeof(map_documents)/sizeof(map_documents[0]);j++){
  const MapDocument *d=map_documents+j;
  if(d->pl!=mpl||d->floor!=floor||!room_shown(pl,floor,d->seen)||bank_bit(d->bank,d->bit)||
     !guards_pass(document_guards+d->guard_start,d->guard_count))continue;
  unsigned t=icon_tex();
  if(!t)break;
  for(unsigned k=0;k<sizeof(overlay_icons)/sizeof(overlay_icons[0]);k++)if(overlay_icons[k].kind==11){
   const OverlayIcon *i=overlay_icons+k;int w=isz(OVERLAY_ICON_TEX/OVERLAY_ICON_SCALE);
   if(!under_high(MX(d->x+PROJ_CENTRE)-w/2,MY(d->y+PROJ_CENTRE)-w/2,w,w)&&!in_panel(MX(d->x+PROJ_CENTRE)-w/2,MY(d->y+PROJ_CENTRE)-w/2,w,w)){icon_quad(11,MX(d->x+PROJ_CENTRE)-w/2,MY(d->y+PROJ_CENTRE)-w/2,w,i,t);name_marker(MX(d->x+PROJ_CENTRE)-w/2,MY(d->y+PROJ_CENTRE)-w/2,w,w,d->item,3);}docmarks++;break;
  }
 }
 for(unsigned j=0;overlay_enabled&&locks_enabled&&j<sizeof(doors)/sizeof(doors[0]);j++){
  const Door*d=doors+j;const Icon *i=door_icon(d,pl,mpl,floor,flags);if(!i)continue;
  int x,y,w,h,cx,cy;door_pos(d,i,dx,dy,&cx,&cy);icon_box(cx,cy,i,&x,&y,&w,&h);
  // A locked box holding a key item shares its star's spot (611 Weapon Box): show the lock as a badge, like area maps.
  int badge=on_marker(high_count,cx,cy);
  if(badge){x+=MAP_BADGE;y+=MAP_BADGE;}
  if((badge?!under_high_except(x,y,w,h,cx,cy):!under_high(x,y,w,h))&&!in_panel(x,y,w,h)){quad_draw(x,y,w,h,i->u,i->v,i->w,i->h,tex);name_marker(x,y,w,h,d->key,0);shown++;}
 }
 unsigned monsters=0;
 for(unsigned j=0;overlay_enabled&&monsters_enabled&&j<sizeof(map_monsters)/sizeof(map_monsters[0]);j++){
  const MapMonster *m=map_monsters+j;
  if(m->pl!=npl||m->floor!=floor||!room_shown(pl,floor,m->seen)||monster_dead(m)||
     !guards_pass(monster_guards+m->guard_start,m->guard_count))continue;
  unsigned t=icon_tex();
  if(!t)break;
  for(unsigned k=0;k<sizeof(overlay_icons)/sizeof(overlay_icons[0]);k++)if(overlay_icons[k].kind==MONSTER_KIND+m->cat){
   const OverlayIcon*i=overlay_icons+k;
   int d=sd_on()?5:isz(6),x=MX(m->x+PROJ_CENTRE)-d/2,y=MY(m->y+PROJ_CENTRE)-d/2;
   if(!under_high(x,y,d,d)&&!in_panel(x,y,d,d))icon_quad(MONSTER_KIND+m->cat,x,y,d,i,t);monsters++;break;
  }
 }
 // Key items and puzzle diamonds were drawn first (draw_key_items); only common/map items remain.
 for(unsigned j=0;overlay_enabled&&j<sizeof(map_items)/sizeof(map_items[0]);j++){
  const MapItem *i=map_items+j;
  if(!item_enabled(i->item)||i->pl!=mpl||i->floor!=floor||!room_shown(pl,floor,i->seen)||bank_bit(i->bank,i->bit))continue;
  if(!guards_pass(map_item_guards+i->guard_start,i->guard_count))continue;
  if(map_item(i->item)||common_item(i->item)){
   unsigned t=icon_tex();
   if(!t)break;
   for(unsigned q=0;q<sizeof(overlay_icons)/sizeof(overlay_icons[0]);q++)if(overlay_icons[q].kind==((i->item>=200&&i->item<=205)?13:100+i->item)){
    const OverlayIcon *icon=overlay_icons+q;int w=isz((OVERLAY_ICON_TEX/OVERLAY_ICON_SCALE*90+50)/100);
    int x=MX(i->x+PROJ_CENTRE)-w/2,y=MY(i->y+PROJ_CENTRE)-w/2;
    // Area maps are progression pickups: when a diamond/star covers the spot (East Office safe holds the police map),
    // show the map as a badge half under its lower-right corner instead of hiding it (user 2026-10-28). The marker it
    // belongs to (the box holding the pickup point) stays on top; generate_room_names keeps the badge box clear.
    int cx=x+w/2,cy=y+w/2,own=map_item(i->item)&&under_high(x,y,w,w);
    if(own){x+=MAP_BADGE;y+=MAP_BADGE;}
    if((own?!under_high_except(x,y,w,w,cx,cy):!under_high(x,y,w,w))&&!in_panel(x,y,w,w)){icon_quad(overlay_icons[q].kind,x,y,w,icon,t);name_marker(x,y,w,w,i->item,map_item(i->item)?2u:4u);}pickups++;break;
   }
  }
 }
 drawing_icons=0;
 draw_marker_names();
 draw_room_names(pl,floor,dx,dy,2);
 help_draw();
 if((frames-1)%120==0)log_line("map floor=%u locks=%u items=%u docs=%u rooms=%u icons=%u monsters=%u enabled=%u tinted=%u texture=%u\n",floor,shown,pickups,docmarks,names,marks,monsters,puzzles_enabled,tinted,tex);
 tinted=0;
}
__declspec(dllexport) unsigned __cdecl KeyMapTestUpload(void){test_texture=0;texture=0;return get_texture();}
__declspec(dllexport) unsigned __cdecl KeyMapTestUploadPage(unsigned i){
 // 0=key atlas, then active-language room/item pages, the icon page and the key art page.
 if(i==0)return create_texture(atlas_pixels);
 unsigned rp=english_enabled?ROOM_LABEL_PAGE_COUNT_EN:ROOM_LABEL_PAGE_COUNT_KO;
 unsigned ip=english_enabled?ITEM_LABEL_PAGE_COUNT_EN:ITEM_LABEL_PAGE_COUNT_KO;
 if(i<=rp)return create_texture(active_room_pixels(i-1));
 if(i-1-rp<ip)return create_texture(active_item_pixels(i-1-rp));
 if(i==1+rp+ip)return create_texture(overlay_icon_pixels);
 if(i==2+rp+ip)return create_texture(key_art_pixels);
 return 0;
}
__declspec(dllexport) int __cdecl KeyMapTestSdMode(int m){if(m>=0)sd_mode=m;return sd_mode;}
__declspec(dllexport) int __cdecl KeyMapTestSdDecide(int mode,const char *cfg){display_mode=mode;sd_mode=-1;lstrcpyA(config_path,cfg);return sd_decide();}
__declspec(dllexport) void __cdecl KeyMapTestTexture(unsigned id){test_texture=1;texture=id;}
__declspec(dllexport) void __cdecl KeyMapTestInit(unsigned char *g){sd_mode=0;game=g;map_draw=(void*)addr(0x4fa990);flat_rect=(void*)addr(0x441170);check_bit=(void*)addr(0x503170);sprite_draw=(void*)addr(0x440280);}
__declspec(dllexport) uintptr_t __cdecl KeyMapTestFillHook(void){return (uintptr_t)fill_stub;}
__declspec(dllexport) void __cdecl KeyMapTestDraw(void){draw_names(*(unsigned char*)addr(0x691f62));}
__declspec(dllexport) void __cdecl KeyMapTestToggle(unsigned mode,int down){update_toggle(mode,down);}
__declspec(dllexport) int __cdecl KeyMapTestState(void){return overlay_enabled|(room_names_enabled<<1)|(locks_enabled<<2)|(items_enabled<<3)|(documents_enabled<<4);}
__declspec(dllexport) int __cdecl KeyMapTestInteractionStage(void){return puzzles_enabled;}
__declspec(dllexport) int __cdecl KeyMapTestLanguage(void){return english_enabled;}
__declspec(dllexport) int __cdecl KeyMapTestMonsters(void){return monsters_enabled;}
__declspec(dllexport) int __cdecl KeyMapTestCommon(void){return common_enabled;}
__declspec(dllexport) int __cdecl KeyMapTestEvents(void){return events_enabled;}
__declspec(dllexport) unsigned __cdecl KeyMapTestOpacity(void){return name_opacity;}
__declspec(dllexport) unsigned __cdecl KeyMapTestOpacityValue(int v){return opacity_value(v);}
__declspec(dllexport) unsigned __cdecl KeyMapTestScope(void){return scope;}
__declspec(dllexport) unsigned __cdecl KeyMapTestSize(void){return name_size;}
__declspec(dllexport) int __cdecl KeyMapTestLegend(void){return legend_enabled;}
__declspec(dllexport) unsigned __cdecl KeyMapTestSizeValue(int v){return size_value(v);}
__declspec(dllexport) unsigned __cdecl KeyMapTestPanel(unsigned i){const Bounds *b=panels+i;return i<panel_count?(unsigned)b->x|(unsigned)b->y<<9|(unsigned)b->w<<17|(unsigned)b->h<<26:0;}
__declspec(dllexport) unsigned __cdecl KeyMapTestIcons(void){return icon_size|icon_opacity<<8|(unsigned)(item_names_enabled!=0)<<16|(unsigned)item_names_enabled<<19|(unsigned)modifier_ctrl<<17|(unsigned)lock_side<<18;}
__declspec(dllexport) void __cdecl KeyMapTestSetIcons(unsigned size,unsigned opacity,int names){icon_size=size;icon_opacity=opacity;item_names_enabled=names;}
__declspec(dllexport) void __cdecl KeyMapTestLockSide(int on){lock_side=on;}
__declspec(dllexport) int __cdecl KeyMapTestSettings(const char *path,int save){lstrcpyA(settings_path,path);return save?save_settings():load_settings();}
// Number keys follow the legend ([0] all .. [9] scope; user 2026-11-08); language moved to the backslash key (VK_OEM_5, shown as
// the won sign on Korean keyboards).
static unsigned map_keys_down(void){return
 ((GetAsyncKeyState('0')&0x8000)?1:0)|((GetAsyncKeyState('1')&0x8000)?2:0)|
 ((GetAsyncKeyState('2')&0x8000)?4:0)|((GetAsyncKeyState('3')&0x8000)?8:0)|
 ((GetAsyncKeyState('4')&0x8000)?16:0)|((GetAsyncKeyState(VK_OEM_5)&0x8000)?32:0)|
 ((GetAsyncKeyState('5')&0x8000)?64:0)|((GetAsyncKeyState('7')&0x8000)?128:0)|
 ((GetAsyncKeyState('8')&0x8000)?256:0)|((GetAsyncKeyState(VK_OEM_PLUS)|GetAsyncKeyState(VK_ADD))&0x8000?512:0)|
 ((GetAsyncKeyState(VK_OEM_MINUS)|GetAsyncKeyState(VK_SUBTRACT))&0x8000?1024:0)|((GetAsyncKeyState(modifier_ctrl?VK_CONTROL:VK_SHIFT)&0x8000)?KEY_MOD:0)|
 ((GetAsyncKeyState('9')&0x8000)?4096:0)|((GetAsyncKeyState(VK_OEM_3)&0x8000)?8192:0)|((GetAsyncKeyState('H')&0x8000)?16384:0)|
 ((GetAsyncKeyState(VK_OEM_4)&0x8000)?32768:0)|((GetAsyncKeyState(VK_OEM_6)&0x8000)?65536:0)|((GetAsyncKeyState('6')&0x8000)?131072:0);}
__declspec(dllexport) unsigned __cdecl KeyMapTestKeys(void){return map_keys_down();}
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
// Off-screen packets stay queued, so they are hidden with the native alpha packet (see quad_draw) instead of moved.
static void zoom_hide(unsigned char *p){*(unsigned*)(p+4)=0x400025;*(unsigned*)(p+28)=0;}
static int zoom_clamp(int v,int hi){return v<0?0:v>hi?hi:v;}
// One map texel becomes 2x2; crops stay even so UVs stay on whole texels. RE3's map_x with a fixed zoom of 200.
static void zoom_axis(unsigned char *p,unsigned axis,int view,int hi){
 short *c=(short*)(p+16)+axis;
 int a=2*c[0]-view,b=2*c[2]+1-view,cut;
 if(a<1){cut=(1-a+1)&~1;a+=cut;p[24+axis]=(unsigned char)(p[24+axis]+cut/2);}
 if(b>hi){cut=(b-hi+1)&~1;b-=cut;p[26+axis]=(unsigned char)(p[26+axis]-cut/2);}
 if(a>b){zoom_hide(p);a=b=1;}
 c[0]=(short)a;c[2]=(short)b;
}
static void zoom_packets(uintptr_t start){
 if(!zoom_on)return;
 unsigned cursor=*(unsigned*)addr(0x67c7d8+20*12),ui=*(unsigned*)addr(0x67c7d8+30*12);
 uintptr_t end=*(uintptr_t*)addr(0x524e1c);
 if(zoom_center){
  zoom_center=0;view_x=view_y=0;
  int cx=160,cy=120;
  for(uintptr_t a=start;a<end;a+=32){ // player cursor (v<24; floor arrows use v 24) if on this floor, else map centre
   unsigned char *p=(unsigned char*)a;short *c=(short*)(p+16);
   if(*(unsigned*)(p+8)==cursor&&p[25]<24){cx=c[0]+6;cy=c[1]+6;break;}
  }
  view_x=zoom_clamp(2*cx-160,320);view_y=zoom_clamp(2*cy-120,240);
 }
 for(uintptr_t a=start;a<end;a+=32){
  unsigned char *p=(unsigned char*)a;unsigned tex=*(unsigned*)(p+8);short *c=(short*)(p+16);
  if(tex==ui||(tex==cursor&&p[25]>=24)){
   // Compass, title and floor arrows keep their place; room outlines (priority 9) would cover them (10): copy on top.
   uintptr_t next=*(uintptr_t*)addr(0x524e1c),limit=*(uintptr_t*)addr(0x524e20);
   if(next>limit||limit-next<32+8192)continue;
   unsigned char *q=(unsigned char*)next;for(unsigned j=0;j<32;j++)q[j]=p[j];
   void (__thiscall *queue)(void*,void*,unsigned)=(void*)addr(0x4021c0);
   queue(*(void**)addr(0x6805b8),q,8);*(uintptr_t*)addr(0x524e1c)=next+32;
  }else if(tex==cursor){ // keeps its size
   int x=2*(c[0]+6)-view_x-6,y=2*(c[1]+6)-view_y-6;
   if(x<1||x>306||y<1||y>226){zoom_hide(p);continue;}
   c[0]=(short)x;c[1]=(short)y;c[2]=(short)(x+11);c[3]=(short)(y+11);
  }else{zoom_axis(p,0,view_x,318);zoom_axis(p,1,view_y,238);}
 }
}
static void draw_map(unsigned mode){
 sd_decide();
 update_toggle(mode,map_keys_down());ensure_native_ui();
 uintptr_t start=*(uintptr_t*)addr(0x524e1c);
 if(scope!=3||!draw_all_room_outlines())map_draw();
 zoom_packets(start);
 draw_names(mode);
}
// Status-screen map: native 0x4fa46b..0x4fa523 changes floor on Up/Down; while zoomed those keys pan instead.
#define FLOOR_SITE 0x4fa465
static void floor_keys(int enabled){
 static const unsigned char on[6]={0x0f,0x89,0xbb,0,0,0},off[6]={0xe9,0xbc,0,0,0,0x90};
 unsigned char *site=(unsigned char*)addr(FLOOR_SITE);DWORD old,unused;
 if(!VirtualProtect(site,6,PAGE_EXECUTE_READWRITE,&old)){log_line("floor key permissions failed\n");return;}
 for(unsigned i=0;i<6;i++)site[i]=enabled?on[i]:off[i];
 VirtualProtect(site,6,old,&unused);FlushInstructionCache(GetCurrentProcess(),site,6);
}
static void zoom_set(int on){
 if(zoom_on==on)return;
 zoom_on=on;zoom_center=on;floor_keys(!on);
}
// Same inputs as RE3 0x4ea61c/0x4ea691: decide (0x988608 bit 0x1000) toggles, held directions (0x9885fc) pan 4 px a frame.
static unsigned zoom_key_was;
static void zoom_input(void){
 unsigned key=*(uint32_t*)addr(0x988608)&0x1000,pad=*(uint32_t*)addr(0x9885fc);
 if(key&~zoom_key_was){
  void (__cdecl *sound)(unsigned,unsigned)=(void*)addr(0x4ed950);
  zoom_set(!zoom_on);sound(0x4040000,0);
 }
 zoom_key_was=key;
 if(!zoom_on||zoom_center)return;
 view_y=zoom_clamp(view_y+(pad&0x4000?4:0)-(pad&0x1000?4:0),240);
 view_x=zoom_clamp(view_x+(pad&0x2000?4:0)-(pad&0x8000?4:0),320);
}
// Not remembered: a pause longer than any frame means the map was closed and reopened.
static void zoom_reopen_check(void){
 static LARGE_INTEGER last;LARGE_INTEGER now={0},rate={0};
 QueryPerformanceFrequency(&rate);QueryPerformanceCounter(&now);
 if(rate.QuadPart&&(!last.QuadPart||now.QuadPart-last.QuadPart>rate.QuadPart/2)){
  zoom_set(0);zoom_key_was=*(uint32_t*)addr(0x988608)&0x1000; // the press that opened the map must not toggle
 }
 last=now;
}
// The status-screen selection handler 0x4fa240 draws at phase3; the ordinary map handler draws at phase0.
static void __cdecl hook_status_selection(void){zoom_reopen_check();zoom_input();draw_map(0);}
static void __cdecl hook_map(void){draw_map(*(unsigned char*)addr(0x691f62));}
static void __cdecl hook_status_entry(void){zoom_set(0);draw_map(0);}
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
#define NAV_S (sd_on()?1:8) /* SD: 1 texel per map pixel */
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
  nav_pixels[y*256+x]=c;nav_pixels[y*256+128+(int)w-1-x]=c;
  nav_pixels[(128+x)*256+y]=c;nav_pixels[(128+(int)w-1-x)*256+128+y]=c; // left cell at u0, mirrored right cell at u128
 }
}
static void nav_arrows_draw(void){
 int pos=floor_pos(*(unsigned char*)addr(0x691f7a));
 if(pos<0)return;
 unsigned area=pos_area(pos),player=player_floor();
 int left=area_step(area,-1,player)>=0,right=area_step(area,1,player)>=0;
 int up=0,down=0;
 for(int p=pos;area==3&&p-->(int)area_start[area];)up|=floor_visited(floor_order[p]);
 for(unsigned p=pos+1;area==3&&p<area_start[area+1];p++)down|=floor_visited(floor_order[p]);
 if(!left&&!right&&!up&&!down)return;
 if(!nav_pixels[NAV_H*NAV_S/2*256+NAV_S])nav_build();
 unsigned tex=cached_texture(&nav_texture,nav_pixels);
 unsigned shade=(*(unsigned char*)addr(0x691f88)+0x28)&0xff;
 quad_color=0xff000000|shade<<16|shade<<8|shade;
 if(left)quad_draw(5,120-NAV_H/2,NAV_W,NAV_H,0,0,NAV_W*NAV_S,NAV_H*NAV_S,tex);
 if(right)quad_draw(315-NAV_W,120-NAV_H/2,NAV_W,NAV_H,128,0,NAV_W*NAV_S,NAV_H*NAV_S,tex);
 if(up)quad_draw(160-NAV_H/2,18,NAV_H,NAV_W,0,128,NAV_H*NAV_S,NAV_W*NAV_S,tex);
 if(down)quad_draw(160-NAV_H/2,196,NAV_H,NAV_W,128,128,NAV_H*NAV_S,NAV_W*NAV_S,tex);
 quad_color=0;
}
// 0x4fb7e7 runs after the status-map handler (index 2 in 0x53db1c) and, after a floor reload, again within the same
// frame while 0x9885fc still holds the press: act on newly pressed directions only, or one press moves two floors.
static unsigned nav_pad_was;
static unsigned nav_press(unsigned pad){pad&=0xf000;unsigned pressed=pad&~nav_pad_was;nav_pad_was=pad;return map_nav(pressed);}
static void __cdecl hook_status_map(void){
 if(*(unsigned char*)addr(0x691f61)!=2){zoom_set(0);hook_map();return;}
 zoom_reopen_check();zoom_input();
 if(zoom_on)nav_pad_was=*(uint32_t*)addr(0x9885fc)&0xf000; // directions pan; a release must not switch floors
 else if(nav_press(*(uint32_t*)addr(0x9885fc)))return; // the floor's map is reloaded first; native skips this frame's draw too
 hook_map();if(!zoom_on)nav_arrows_draw();
}
__declspec(dllexport) void __cdecl KeyMapTestDrawMap(void){draw_map(0);}
__declspec(dllexport) void __cdecl KeyMapTestZoomInput(void){zoom_input();}
__declspec(dllexport) void __cdecl KeyMapTestZoomView(int x,int y){view_x=x;view_y=y;}
__declspec(dllexport) int __cdecl KeyMapTestZoomState(void){return zoom_on;}
__declspec(dllexport) int __cdecl KeyMapTestZoomX(void){return view_x;}
__declspec(dllexport) int __cdecl KeyMapTestZoomY(void){return view_y;}
__declspec(dllexport) unsigned __cdecl KeyMapTestNav(unsigned pad){return map_nav(pad);}
__declspec(dllexport) unsigned __cdecl KeyMapTestNavPress(unsigned pad){return nav_press(pad);}
__declspec(dllexport) void __cdecl KeyMapTestNavArrows(void){nav_arrows_draw();}
__declspec(dllexport) uintptr_t __cdecl KeyMapTestNavPixels(void){nav_build();return (uintptr_t)nav_pixels;}
BOOL WINAPI DllMain(HINSTANCE module,DWORD reason,LPVOID reserved){
 (void)reserved;if(reason!=DLL_PROCESS_ATTACH)return TRUE;
 DisableThreadLibraryCalls(module);game=(unsigned char*)GetModuleHandleW(NULL);
 char own[MAX_PATH];GetModuleFileNameA(module,own,sizeof(own));char *slash=NULL;for(char *p=own;*p;p++)if(*p=='\\')slash=p;
 if(slash){lstrcpyA(slash+1,"RE2.AnnotatedMap.ini");lstrcpyA(settings_path,own);lstrcpyA(slash+1,"RE2.AnnotatedMap.log");}else{lstrcpyA(own,"RE2.AnnotatedMap.log");lstrcpyA(settings_path,"RE2.AnnotatedMap.ini");}
 int migrate=load_settings();
 {char cfg[MAX_PATH];if(GetModuleFileNameA(NULL,cfg,sizeof(cfg))){char *sl=NULL;for(char *p=cfg;*p;p++)if(*p=='\\')sl=p;if(sl){lstrcpyA(sl+1,"config.ini");lstrcpyA(config_path,cfg);}}} // Classic REbirth config.ini beside the game exe
 logfile=CreateFileA(own,GENERIC_WRITE,FILE_SHARE_READ,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
 if(migrate&&GetFileAttributesA(settings_path)!=INVALID_FILE_ATTRIBUTES&&save_settings())log_line("settings rewritten as version %u\n",SETTINGS_VERSION);
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
 const unsigned char floor_jns[]={0x0f,0x89,0xbb,0x00,0x00,0x00};
 if(!equal((void*)addr(FLOOR_SITE),floor_jns,sizeof(floor_jns))){log_line("unsupported status floor switch; no patch applied\n");return TRUE;}
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
