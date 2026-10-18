"""Gerçekçi 3D stil testi: Blender Cycles (bpy, pip ile kurulu) ile kozmetik ürün reklamı.

Uydurma marka: LÉVA Hyaluron Serum. Amber cam damlalıklı şişe, travertin kaideler,
pencere jaluzisi gölgesi (gobo), yumuşak alan ışıkları, gerçek alan derinliği, kamera hareketi.
Her şey t'nin saf fonksiyonu; kare kare PNG (16 bit) üretir, yazılar sonradan bindir.py ile eklenir.

Kullanım (bpy kurulu bir Python ile):
  python sahne.py kare  ÇIKTI_KLASÖRÜ t1 t2 ...  [--olcek 0.5] [--ornek 32]
  python sahne.py video ÇIKTI_KLASÖRÜ [--bas 0] [--son 240] [--olcek 1] [--ornek 64]
"""
import math, os, sys, time
import bpy, bmesh
from mathutils import Vector
from PIL import Image, ImageDraw, ImageFont

BURADA = os.path.dirname(os.path.abspath(__file__))
FPS, SURE = 24, 10.0
W, H = 1080, 1920

# ---------------------------------------------------------------- yardımcılar

def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def smooth(p): p = clamp(p); return p * p * p * (p * (p * 6 - 15) + 10)
def lerp(a, b, p): return a + (b - a) * p


def torna(ad, profil, seg=160, kapat=False, uv=False):
    """(r, z) profilini Z ekseni etrafında döndürür. kapat=True ise profil kapalı halka."""
    if kapat: profil = list(profil) + [profil[0]]
    n, kol = len(profil), seg + (1 if uv else 0)
    verts = []
    for i in range(kol):
        a = 2 * math.pi * i / seg
        for r, z in profil: verts.append((r * math.cos(a), r * math.sin(a), z))
    faces = []
    for i in range(seg):
        i2 = i + 1 if uv else (i + 1) % seg
        for j in range(n - 1):
            faces.append((i * n + j, i2 * n + j, i2 * n + j + 1, i * n + j + 1))
    me = bpy.data.meshes.new(ad)
    me.from_pydata(verts, [], faces)
    if uv:
        lay = me.uv_layers.new(name='UV')
        zs = [z for _, z in profil]; z0, z1 = min(zs), max(zs)
        for poly in me.polygons:
            for li in poly.loop_indices:
                vi = me.loops[li].vertex_index
                lay.data[li].uv = ((vi // n) / seg, (profil[vi % n][1] - z0) / (z1 - z0))
    bm = bmesh.new(); bm.from_mesh(me)
    if not uv: bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new(ad, me); bpy.context.collection.objects.link(ob)
    return ob


def malzeme(ad, **k):
    m = bpy.data.materials.new(ad); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    ad_esle = {'renk': 'Base Color', 'puruz': 'Roughness', 'metal': 'Metallic', 'ior': 'IOR',
               'gecirgen': 'Transmission Weight', 'kaplama': 'Coat Weight', 'kaplama_puruz': 'Coat Roughness',
               'aniso': 'Anisotropic', 'yuzey_alti': 'Subsurface Weight', 'parlak': 'Specular IOR Level'}
    for a, v in k.items():
        if a == 'renk': v = (*v, 1.0)
        b.inputs[ad_esle[a]].default_value = v
    return m, b


def ata(ob, m): ob.data.materials.clear(); ob.data.materials.append(m)


def gurultu_renk(m, b, r1, r2, olcek=40.0, detay=6.0, bump=0.15, puruz=None):
    """Taş / sıva için gürültüyle karışan iki renk + kabartma."""
    nt = m.node_tree; N = nt.nodes
    tc = N.new('ShaderNodeTexCoord')
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = olcek; nz.inputs['Detail'].default_value = detay
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    ramp = N.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*r1, 1); ramp.color_ramp.elements[1].color = (*r2, 1)
    ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[1].position = 0.65
    nt.links.new(nz.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    if bump:
        # travertin gözenekleri: ince uzun damarlar (Z'de basık gürültü)
        mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1.0, 1.0, 7.0)
        nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
        nz2 = N.new('ShaderNodeTexNoise'); nz2.inputs['Scale'].default_value = olcek * 2.2; nz2.inputs['Detail'].default_value = 3
        nt.links.new(mp.outputs['Vector'], nz2.inputs['Vector'])
        bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = bump; bp.inputs['Distance'].default_value = 0.0006
        nt.links.new(nz2.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])


# ---------------------------------------------------------------- etiket dokusu

def etiket_dokusu(yol):
    """Şişe çevresine sarılan serigrafi baskı: beyaz mürekkep, saydam zemin. u=0.75 kameraya bakar."""
    CW, CH = 6144, 2260  # çevre 0.1414 m x yükseklik 0.052 m
    im = Image.new('RGBA', (CW, CH), (255, 255, 255, 0)); d = ImageDraw.Draw(im)
    serif = os.path.join(BURADA, 'fonts', 'CormorantGaramond.ttf'); sans = os.path.join(BURADA, 'fonts', 'Inter.ttf')
    def font(yol, px, agirlik):
        f = ImageFont.truetype(yol, px)
        try: f.set_variation_by_axes([agirlik] if 'Cormorant' in yol else [14, agirlik])
        except Exception: pass
        return f
    cx = int(CW * 0.75)
    def yaz(metin, f, y, aralik=0):
        harfler = list(metin)
        gen = sum(f.getlength(h) for h in harfler) + aralik * (len(harfler) - 1)
        x = cx - gen / 2
        for h in harfler:
            d.text((x, y), h, font=f, fill=(250, 246, 238, 255)); x += f.getlength(h) + aralik
    yaz('LÉVA', font(serif, 500, 500), 470, aralik=60)
    d.rectangle((cx - 230, 1110, cx + 230, 1116), fill=(250, 246, 238, 255))
    yaz('HYALURON SERUM', font(sans, 118, 500), 1200, aralik=26)
    yaz('%2 HYALURONİK ASİT  ·  B5', font(sans, 74, 400), 1420, aralik=10)
    yaz('30 ml  ·  1.0 fl oz', font(sans, 74, 400), 1950, aralik=10)
    im.save(yol)


# ---------------------------------------------------------------- sahne

def sahne_kur(olcek, ornek):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import addon_utils
    addon_utils.enable('cycles', default_set=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    cy = sc.cycles
    cy.device = 'CPU'; cy.samples = ornek; cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.03
    cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'
    cy.max_bounces = 12; cy.diffuse_bounces = 2; cy.glossy_bounces = 4; cy.transmission_bounces = 10
    cy.transparent_max_bounces = 8; cy.caustics_reflective = False; cy.caustics_refractive = False
    cy.sample_clamp_indirect = 6.0; cy.blur_glossy = 1.0
    cy.seed = 7; cy.use_animated_seed = False
    sc.render.use_persistent_data = True
    sc.render.resolution_x, sc.render.resolution_y = int(W * olcek), int(H * olcek)
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_depth = '16'
    sc.render.image_settings.color_mode = 'RGB'
    sc.view_settings.view_transform = 'AgX'
    for look in ('AgX - Medium High Contrast', 'Medium High Contrast'):
        try: sc.view_settings.look = look; break
        except Exception: pass
    sc.view_settings.exposure = -0.45

    # dünya: Blender'ın kendi stüdyo HDRI'si (yansımalar için), düşük güç
    dunya = bpy.data.worlds.new('dunya'); sc.world = dunya; dunya.use_nodes = True
    N = dunya.node_tree.nodes; bg = N['Background']
    env = N.new('ShaderNodeTexEnvironment')
    hdri = os.path.join(bpy.utils.resource_path('LOCAL'), 'datafiles', 'studiolights', 'world', 'interior.exr')
    env.image = bpy.data.images.load(hdri)
    dunya.node_tree.links.new(env.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = 0.35

    # --- fon: zemin + kavisli duvar (sonsuz stüdyo fonu)
    prof = [(-1.2, 0.0)] + [(0.18 + 0.32 * math.sin(a), 0.32 - 0.32 * math.cos(a)) for a in [i * math.pi / 2 / 24 for i in range(25)]] + [(0.50, 1.6)]
    verts = [];
    for x in (-1.5, 1.5):
        for y, z in prof: verts.append((x, y, z))
    n = len(prof); faces = [(j, j + 1, n + j + 1, n + j) for j in range(n - 1)]
    me = bpy.data.meshes.new('fon'); me.from_pydata(verts, [], faces)
    for p in me.polygons: p.use_smooth = True
    fon = bpy.data.objects.new('fon', me); sc.collection.objects.link(fon)
    m, b = malzeme('siva', puruz=0.92)
    gurultu_renk(m, b, (0.50, 0.38, 0.29), (0.54, 0.42, 0.32), olcek=18, detay=4, bump=0.05)
    ata(fon, m)

    # --- travertin kaideler
    def kaide(ad, r, h, x, y, z0=0.0):
        p = [(0, z0), (r - 0.002, z0), (r, z0 + 0.002), (r, z0 + h - 0.0015), (r - 0.0015, z0 + h), (0, z0 + h)]
        ob = torna(ad, p, seg=192); ob.location = (x, y, 0); return ob
    k1 = kaide('kaide1', 0.065, 0.036, 0.0, 0.0)
    k2 = kaide('kaide2', 0.050, 0.018, 0.105, 0.075)
    m, b = malzeme('travertin', puruz=0.55)
    gurultu_renk(m, b, (0.60, 0.49, 0.37), (0.74, 0.63, 0.50), olcek=55, detay=8, bump=0.6)
    ata(k1, m); ata(k2, m)

    Z = 0.036  # şişe tabanı (kaide üstü)

    # --- amber cam şişe (kalın cidarlı kapalı kabuk)
    dis = [(0, 0), (0.019, 0), (0.0221, 0.0012), (0.0225, 0.004), (0.0225, 0.078), (0.0222, 0.082), (0.0210, 0.0858),
           (0.0180, 0.0889), (0.0138, 0.0912), (0.0108, 0.0928), (0.0100, 0.0950), (0.0100, 0.1040), (0.0094, 0.1050)]
    ic = [(0.0079, 0.1045), (0.0078, 0.0945), (0.0105, 0.0905), (0.0150, 0.0880), (0.0185, 0.0850), (0.0199, 0.0805),
          (0.0201, 0.0080), (0.0196, 0.0058), (0.0180, 0.0050), (0, 0.0050)]
    sise = torna('sise', dis + ic, seg=192); sise.location.z = Z
    m, b = malzeme('amber', renk=(0.80, 0.36, 0.08), puruz=0.0, gecirgen=1.0, ior=1.52)
    ata(sise, m)

    # --- serum (sıvı), cam iç yüzeyinden çok az içeride
    sivi = torna('sivi', [(0, 0.0053), (0.0178, 0.0053), (0.0194, 0.0060), (0.01985, 0.0080), (0.01985, 0.0640),
                          (0.0150, 0.0646), (0, 0.0648)], seg=192)
    sivi.location.z = Z
    m, b = malzeme('serum', renk=(1.0, 0.80, 0.45), puruz=0.0, gecirgen=1.0, ior=1.36)
    ata(sivi, m)

    # --- pipet camı (ince tüp) ve içindeki serum
    pipet = torna('pipet', [(0, 0.020), (0.0014, 0.020), (0.0030, 0.026), (0.0030, 0.108), (0.0020, 0.108),
                            (0.0020, 0.027), (0.0009, 0.0215), (0, 0.0215)], seg=96)
    pipet.location.z = Z
    m, b = malzeme('seffaf_cam', renk=(1, 1, 1), puruz=0.0, gecirgen=1.0, ior=1.5)
    ata(pipet, m)

    # --- altın bilezik (eloksal alüminyum, fırçalı)
    bilezik = torna('bilezik', [(0.0102, 0.0925), (0.0127, 0.0925), (0.0130, 0.0938), (0.0130, 0.1108), (0.0127, 0.1121),
                                 (0.0090, 0.1121), (0.0, 0.1121), (0.0, 0.1062), (0.0102, 0.1062)], seg=192, kapat=True)
    bilezik.location.z = Z
    m, b = malzeme('altin', renk=(0.96, 0.78, 0.50), metal=1.0, puruz=0.22, aniso=0.7)
    nt = m.node_tree; tc = nt.nodes.new('ShaderNodeTexCoord'); wv = nt.nodes.new('ShaderNodeTexWave')
    wv.wave_type = 'RINGS'; wv.rings_direction = 'Z'; wv.inputs['Scale'].default_value = 600; wv.inputs['Distortion'].default_value = 0
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.0; bp.inputs['Distance'].default_value = 0.0002
    # dikey tırtıl: açısal halkalar (bilezik çevresi boyunca)
    nt.links.new(tc.outputs['Object'], wv.inputs['Vector'])
    m_altin = m
    ata(bilezik, m)

    # --- kauçuk puar
    puar = torna('puar', [(0, 0.1121), (0.0086, 0.1121), (0.0091, 0.1150), (0.0089, 0.1220), (0.0080, 0.1300),
                          (0.0082, 0.1390), (0.0077, 0.1450), (0.0062, 0.1495), (0.0035, 0.1515), (0, 0.1520)], seg=160)
    puar.location.z = Z
    m, b = malzeme('kaucuk', renk=(0.018, 0.016, 0.015), puruz=0.42, kaplama=0.25, kaplama_puruz=0.3)
    ata(puar, m)

    # --- serigrafi etiket (şişeye sarılı ince kabuk, saydam zemin)
    doku = os.path.join(BURADA, '_etiket.png')
    if not os.path.exists(doku): etiket_dokusu(doku)
    bant = torna('etiket', [(0.02257, 0.016), (0.02257, 0.068)], seg=256, uv=True)
    bant.location.z = Z
    m = bpy.data.materials.new('baski'); m.use_nodes = True; nt = m.node_tree; Nn = nt.nodes
    pr = Nn['Principled BSDF']; pr.inputs['Base Color'].default_value = (0.92, 0.89, 0.84, 1); pr.inputs['Roughness'].default_value = 0.38
    tx = Nn.new('ShaderNodeTexImage'); tx.image = bpy.data.images.load(doku); tx.interpolation = 'Cubic'
    tr = Nn.new('ShaderNodeBsdfTransparent'); mx = Nn.new('ShaderNodeMixShader'); out = Nn['Material Output']
    nt.links.new(tx.outputs['Alpha'], mx.inputs['Fac']); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(pr.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs['Surface'])
    ata(bant, m)

    # --- krem kavanozu (seramik beyaz) + altın kapak, arka sağda ikinci kaide üstünde
    kav = torna('kavanoz', [(0, 0), (0.028, 0), (0.0305, 0.002), (0.031, 0.006), (0.031, 0.030), (0.0295, 0.033), (0, 0.033)], seg=192)
    kav.location = (0.105, 0.075, 0.018)
    m, b = malzeme('seramik', renk=(0.93, 0.91, 0.87), puruz=0.32, kaplama=0.6, kaplama_puruz=0.08, yuzey_alti=0.08)
    ata(kav, m)
    kap = torna('kapak', [(0, 0.033), (0.0312, 0.033), (0.0318, 0.0345), (0.0318, 0.0478), (0.0310, 0.0490), (0, 0.0492)], seg=192)
    kap.location = (0.105, 0.075, 0.018); ata(kap, m_altin)

    # --- ışıklar
    # güneş + jaluzi (gobo): fonda ve ürünlerde yumuşak çizgili gölge
    bpy.ops.object.light_add(type='SUN'); gunes = bpy.context.object
    gunes.data.energy = 6.5; gunes.data.angle = math.radians(1.6); gunes.data.color = (1.0, 0.86, 0.70)
    yon = Vector((-0.55, -0.45, 0.70)).normalized()  # ışığın geldiği yön (sol-ön-yukarı)
    gunes.rotation_euler = yon.to_track_quat('Z', 'Y').to_euler()
    jal = bpy.data.objects.new('jaluzi', None); sc.collection.objects.link(jal)
    for i in range(-14, 15):
        bpy.ops.mesh.primitive_cube_add(size=1)
        c = bpy.context.object; c.scale = (2.0, 0.018, 0.002); c.location = (0, i * 0.030, 0); c.parent = jal
        c.visible_camera = False; c.visible_glossy = False; c.visible_transmission = False; c.visible_diffuse = False
    merkez = Vector((0, 0.05, 0.08)) + yon * 0.9
    jal.location = merkez
    jal.rotation_euler = yon.to_track_quat('Z', 'X').to_euler()
    jal.rotation_euler.rotate_axis('Z', math.radians(28))

    # büyük yumuşak ana ışık (kamera solu) ve sıcak dolgu
    def alan(ad, boy, guc, renk, konum, hedef, sekil='RECTANGLE', boy2=None):
        bpy.ops.object.light_add(type='AREA'); L = bpy.context.object; L.name = ad
        L.data.shape = sekil; L.data.size = boy; L.data.size_y = boy2 or boy
        L.data.energy = guc; L.data.color = renk; L.location = konum
        L.rotation_euler = (Vector(hedef) - Vector(konum)).to_track_quat('-Z', 'Y').to_euler()
        return L
    alan('anahtar', 0.9, 22, (1.0, 0.95, 0.90), (-0.75, -0.55, 0.55), (0, 0, 0.09))
    alan('dolgu', 1.2, 6, (1.0, 0.92, 0.84), (0.8, -0.9, 0.25), (0, 0, 0.08))
    # arkadan dikey ince şerit ışık: camın kenar çizgisi; zamanla süpürür
    serit = alan('serit', 0.05, 26, (1.0, 0.97, 0.94), (0.0, 0.42, 0.10), (0, 0, 0.08), boy2=0.75)
    serit.visible_camera = False
    serit2 = alan('serit2', 0.04, 14, (1.0, 0.97, 0.94), (0.30, 0.30, 0.10), (0, 0, 0.08), boy2=0.75)
    serit2.visible_camera = False

    # kamera
    cam_d = bpy.data.cameras.new('kamera'); cam = bpy.data.objects.new('kamera', cam_d); sc.collection.objects.link(cam)
    sc.camera = cam; cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 24.0
    cam_d.dof.use_dof = True; cam_d.clip_start = 0.005
    return dict(sc=sc, cam=cam, jal=jal, jal0=merkez.copy(), serit=serit, Z=Z)


# ---------------------------------------------------------------- hareket (t'nin saf fonksiyonu)

# anahtar pozlar: (az derece, mesafe m, kamera yüksekliği, hedef z, odak uzaklığı mm, f-sayısı, hedef x kayması)
POZ = [
    (-24.0, 0.34, 0.075, 0.074, 100.0, 2.4, 0.000),   # 0.0 sn  etikete yakın, soldan
    (-6.0, 0.37, 0.080, 0.078, 100.0, 2.8, 0.000),    # 3.6 sn  etiket karşıda
    (-2.0, 0.90, 0.170, 0.125, 70.0, 4.0, 0.050),     # 7.2 sn  geri çekilip kaideyi ve kavanozu göster
    (-8.0, 0.93, 0.175, 0.128, 70.0, 4.0, 0.050),     # 10 sn  yavaş süzülme (üstte yazı alanı)
]
ZAMAN = [0.0, 3.6, 7.2, 10.0]


def poz(t):
    """Anahtar pozlar arasında kübik Hermite (hız kesintisiz); başta hafif akış, sonda yumuşak duruş."""
    t = clamp(t, 0.0, SURE)
    i = min(len(ZAMAN) - 2, max(k for k in range(len(ZAMAN) - 1) if ZAMAN[k] <= t))
    t0, t1 = ZAMAN[i], ZAMAN[i + 1]; h = t1 - t0; p = (t - t0) / h
    def egim(k, j):
        if k == 0: return 0.5 * (POZ[1][j] - POZ[0][j]) / (ZAMAN[1] - ZAMAN[0])
        if k == len(ZAMAN) - 1: return 0.0
        return (POZ[k + 1][j] - POZ[k - 1][j]) / (ZAMAN[k + 1] - ZAMAN[k - 1])
    h00, h10, h01, h11 = 2*p**3 - 3*p**2 + 1, p**3 - 2*p**2 + p, -2*p**3 + 3*p**2, p**3 - p**2
    return [h00 * POZ[i][j] + h10 * h * egim(i, j) + h01 * POZ[i + 1][j] + h11 * h * egim(i + 1, j) for j in range(len(POZ[0]))]


def kare_ayarla(d, t):
    az, mes, ky, hz, odak, f, hx = poz(t)
    a = math.radians(az)
    sag = Vector((math.cos(a), math.sin(a), 0.0))
    hedef = Vector((0.0, 0.0, hz)) + sag * hx
    konum = Vector((mes * math.sin(a), -mes * math.cos(a), ky)) + sag * hx
    cam = d['cam']; cam.location = konum
    cam.rotation_euler = (hedef - konum).to_track_quat('-Z', 'Y').to_euler()
    cd = cam.data; cd.lens = odak; cd.dof.aperture_fstop = f
    # odak: şişenin kameraya bakan yüzü (etiket)
    cd.dof.focus_distance = max(0.05, (Vector((0, 0, hz)) - konum).length - 0.0225)
    # jaluzi gölgesi yavaşça kayar
    d['jal'].location = d['jal0'] + Vector((0.0, 0.0, 0.0)) + Vector((0.020 * t, -0.012 * t, 0.0))
    # arka şerit ışık 0.4-3.4 sn arası soldan sağa süpürür (camda hareket eden parlama)
    s = smooth((t - 0.3) / 3.4)
    d['serit'].location = Vector((lerp(-0.34, 0.34, s), 0.42, 0.10))
    d['serit'].rotation_euler = (Vector((0, 0, 0.08)) - d['serit'].location).to_track_quat('-Z', 'Y').to_euler()


def main():
    arg = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    kip, cikti = arg[0], arg[1]
    def secenek(ad, vars):
        return type(vars)(arg[arg.index(ad) + 1]) if ad in arg else vars
    olcek = secenek('--olcek', 1.0); ornek = secenek('--ornek', 12)
    os.makedirs(cikti, exist_ok=True)
    d = sahne_kur(olcek, ornek); sc = d['sc']
    if kip == 'kare':
        ts, k = [], 2
        while k < len(arg):
            if arg[k].startswith('--'): k += 2; continue
            ts.append(float(arg[k])); k += 1
        isler = [(t, os.path.join(cikti, f'kare-{t:05.2f}.png')) for t in ts]
    else:
        bas, son = secenek('--bas', 0), secenek('--son', int(FPS * SURE))
        isler = [(i / FPS, os.path.join(cikti, f'{i:04d}.png')) for i in range(bas, son)]
    t0 = time.time()
    for j, (t, yol) in enumerate(isler):
        if os.path.exists(yol) and kip == 'video': continue
        kare_ayarla(d, t)
        sc.render.filepath = yol
        bpy.ops.render.render(write_still=True)
        print(f'[{j + 1}/{len(isler)}] t={t:.2f} {time.time() - t0:.0f} sn', flush=True)


if __name__ == '__main__':
    main()
