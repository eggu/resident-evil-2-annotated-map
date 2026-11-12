/* SD mode drawing (2026-11-12): 1:1 sprites of sd_assets.h through quad_draw. Included by re2_keymap.c after the panel helpers. */
static unsigned sd_kind_sprite(unsigned kind){
 switch(kind){case 9:return SD_TYPEWRITER;case 10:return SD_ITEMBOX;case 11:return SD_FILE;case 12:return SD_PUZZLE;case 13:return SD_MAP;
  case 14:case 15:return SD_KEY;case 16:return SD_EVENT;}
 if(kind>=MONSTER_KIND&&kind<MONSTER_KIND+12)return SD_ENEMY;
 if(kind>=100&&kind<141)return sd_common_sprite[kind-100];
 return 0xFFFF;
}
// A marker drawn in its w x w box: the HD atlas cell, or in SD the sprite of its kind centred in the box.
static void icon_quad(unsigned kind,int x,int y,int w,const OverlayIcon *i,unsigned t){
 if(sd_on()){
  unsigned id=sd_kind_sprite(kind);if(id==0xFFFF)return;
  const SdSprite *s=sd_sprites+id;quad_draw(x+(w-s->w)/2,y+(w-s->h)/2,s->w,s->h,s->u,s->v,s->w,s->h,t);return;
 }
 quad_draw(x,y,w,w,i->u,i->v,OVERLAY_ICON_TEX,OVERLAY_ICON_TEX,t);
}
static void sd_put(int x,int y,unsigned id){
 const SdSprite *s=sd_sprites+id;unsigned t=sd_texture(s->page);
 if(t)quad_draw(x,y,s->w,s->h,s->u,s->v,s->w,s->h,t);
}
// A 1 px leader between two points as rectangles: runs of equal minor coordinate (shallow: rows, steep: columns). The raster
// is tools/mapgen/sd_place.py raster() (round half away from zero), so the drawn pixels are the ones the layout checked.
static int sd_round(int a,int n){return (2*a+(a>=0?n:-n))/(2*n);}
static void sd_line(int x0,int y0,int x1,int y1){
 const SdSprite *s=sd_sprites+SD_LEADER;unsigned t=sd_texture(s->page);
 if(!t)return;
 int dx=x1-x0,dy=y1-y0,n=(dx<0?-dx:dx)>(dy<0?-dy:dy)?(dx<0?-dx:dx):(dy<0?-dy:dy),steep=(dy<0?-dy:dy)>(dx<0?-dx:dx);
 int ax=x0,ay=y0,bx=x0,by=y0;
 for(int i=1;i<=n+1;i++){
  int cx=i<=n?x0+sd_round(dx*i,n):0,cy=i<=n?y0+sd_round(dy*i,n):0;
  if(i<=n&&(steep?cx==ax:cy==ay)){bx=cx;by=cy;continue;}
  quad_draw(ax<bx?ax:bx,ay<by?ay:by,(ax<bx?bx-ax:ax-bx)+1,(ay<by?by-ay:ay-by)+1,s->u+2,s->v+2,1,1,t);
  ax=bx=cx;ay=by=cy;
 }
}
// Room names fixed at build time (sd_layout.py), 1x and zoomed: the leader's start follows the map, the name keeps its offset
// to the leader's end. A name cut by the screen edge or under the legend moves inside and its leader re-ends on it (RE3 rule).
static unsigned sd_room_names(unsigned pl,unsigned floor,int dx,int dy){
 unsigned names=0;
 const SdRoom *table=english_enabled?sd_rooms_en:sd_rooms_ko;
 for(unsigned j=0;overlay_enabled&&room_names_enabled&&j<active_room_count();j++){
  const RoomName *r=active_room_names()+j;
  if(r->pl!=pl||r->floor!=floor||!room_shown(pl,floor,r->seen)||table[j].sprite==0xFFFF)continue;
  const SdRoom *o=table+j;const SdSprite *sp=sd_sprites+o->sprite;
  int n=o->n,px[3]={0},py[3]={0},x,y;
  for(int k=0;k<n;k++){px[k]=MX(o->pt[2*k]);py[k]=MY(o->pt[2*k+1]);}
  if(n){x=px[n-1]+o->x-o->pt[2*n-2];y=py[n-1]+o->y-o->pt[2*n-1];}
  else{x=MX(o->x+sp->w/2)-sp->w/2;y=MY(o->y+sp->h/2)-sp->h/2;}
  if(zoom_on&&(n?px[0]<0||px[0]>=320||py[0]<0||py[0]>=240:x+sp->w<0||x>=320||y+sp->h<0||y>=240))continue; // the room is off screen: so is its name
  int nx=x<2?2:x+sp->w>318?318-sp->w:x,ny=y<2?2:y+sp->h>238?238-sp->h:y;
  for(unsigned m=0;m<panel_count;m++){
   const Bounds *b=panels+m;
   if(nx<b->x+b->w&&b->x<nx+sp->w&&ny<b->y+b->h&&b->y<ny+sp->h)ny=b->y-2-sp->h;
  }
  if(n>1&&(nx!=x||ny!=y)){
   int qx=px[n-2],qy=py[n-2];
   px[n-1]=qx<nx?nx-1:qx>=nx+sp->w?nx+sp->w:qx;py[n-1]=qy<ny?ny-1:qy>=ny+sp->h?ny+sp->h:qy;
  }
  for(int k=1;k<n;k++)sd_line(px[k-1],py[k-1],px[k],py[k]);
  sd_put(nx,ny,o->sprite);names++;
 }
 return names;
}
// Legend: 3 columns of 4 rows under a title line, bottom left, as text with the 1 px shadow (a translucent panel would draw beneath
// the opaque map). Its box feeds panels[] like the HD legend, so markers under it are not drawn and names move off it. No readout,
// item-name, size or opacity rows in SD.
static void sd_legend_draw(void){
 panel_count=0;
 const unsigned l=english_enabled?0:1;
 if(!legend_enabled){
  const SdSprite *f=sd_sprites+sd_fold[l];int h=f->h+2;
  panels[panel_count++]=(Bounds){2,238-h,f->w+4,h};
  if(help_draw_mode)sd_put(4,238-h+1,sd_fold[l]);
  return;
 }
 const int on[9]={overlay_enabled,room_names_enabled,locks_enabled,items_enabled,documents_enabled,puzzles_enabled,events_enabled,common_enabled,monsters_enabled};
 unsigned id[12];
 for(unsigned r=0;r<9;r++)id[r]=sd_legend[l][r][on[r]&&(r==0||overlay_enabled)];
 id[9]=sd_scope[l][scope-1];id[10]=sd_lang[l];id[11]=sd_zoom[l][zoom_on?1:0];
 int colw[3]={0,0,0};
 for(unsigned n=0;n<12;n++)if(sd_sprites[id[n]].w>colw[n/4])colw[n/4]=sd_sprites[id[n]].w;
 int width=colw[0]+colw[1]+colw[2]+16,head=sd_sprites[sd_title[l]].w+8+sd_sprites[sd_hide[l]].w;
 if(head>width)width=head;
 int h=5*11+4,x=2,y=238-h;
 panels[panel_count++]=(Bounds){x,y,width+6,h};
 if(!help_draw_mode)return;
 sd_put(x+3,y+2,sd_title[l]);sd_put(x+3+sd_sprites[sd_title[l]].w+8,y+2,sd_hide[l]);
 int cx[3]={x+3,x+3+colw[0]+8,x+3+colw[0]+colw[1]+16};
 for(unsigned n=0;n<12;n++)sd_put(cx[n/4],y+2+11*(1+(int)(n%4)),id[n]);
}
