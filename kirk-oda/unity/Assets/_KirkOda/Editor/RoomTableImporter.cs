using System;
using System.IO;
using KirkOda.Core;
using KirkOda.Data;
using KirkOda.Tooling;
using UnityEditor;
using UnityEngine;

namespace KirkOda.EditorTools
{
    /// <summary>
    /// kirk-oda.md tablosundan RoomDefinition ve GuardianDefinition varlıklarını üretir ya da günceller
    /// (08-dikey-dilim-plani.md, "2–8 Kas" satırı). Yalnız tablonun söylediği alanlara yazar; diorama,
    /// emitter, kamera ve modül referansları elle kurulur ve yeniden üretimde korunur.
    /// </summary>
    public static class RoomTableImporter
    {
        public const string RoomFolder = "Assets/_KirkOda/Data/Rooms";
        public const string GuardianFolder = "Assets/_KirkOda/Data/Guardians";

        /// <summary>Dikey dilim: Toprak'ın ilk üç odası ve Su, Gölge, Ayna gri kutuları. Kırk oda dilimden sonra.</summary>
        public static readonly string[] VerticalSlice = { "R1-01", "R1-02", "R1-03", "R2-01", "R4-02", "R5-04" };

        [MenuItem("Kirk Oda/Odaları tablodan üret (dikey dilim)")]
        public static void GenerateVerticalSlice() => Generate(VerticalSlice);

        public static void Generate(string[] roomIds)
        {
            string path = RoomTableParser.LocateTable(Application.dataPath);
            if (path == null)
            {
                Debug.LogError($"{RoomTableParser.RelativePath} bulunamadı; proje kirk-oda/unity altında açılmalı.");
                return;
            }

            var table = RoomTableParser.Parse(File.ReadAllText(path));
            EnsureFolder(RoomFolder);
            EnsureFolder(GuardianFolder);

            int created = 0, updated = 0;
            foreach (string id in roomIds)
            {
                if (!table.TryGetValue(id, out var row)) throw new ArgumentException($"{id} tabloda yok", nameof(roomIds));

                var guardian = Upsert<GuardianDefinition>($"{GuardianFolder}/G-{row.Id}.asset", g => ApplyGuardian(row, g), out _);
                Upsert<RoomDefinition>($"{RoomFolder}/Room_{row.Id}.asset", r => ApplyRoom(row, guardian, r), out bool isNew);
                if (isNew) created++; else updated++;
            }

            AssetDatabase.SaveAssets();
            Debug.Log($"Kırk Oda: {created} oda üretildi, {updated} oda güncellendi ({Path.GetFileName(path)}).");
        }

        static void ApplyRoom(RoomRow row, GuardianDefinition guardian, RoomDefinition room)
        {
            room.id = row.Id;
            room.ring = row.Ring;
            room.index = row.Index;
            room.guardian = guardian;
            room.oneLinerKey = row.Puzzle;         // tasarım notu; oyunda gösterilmez
            room.halKind = row.Hal;
            room.estimatedMinutes = row.EstimatedMinutes;

            if (row.Ring == RingId.Sessizlik)
                room.hintSteps = Array.Empty<HintStepDef>();
            else if (row.Ring != RingId.An && (room.hintSteps == null || room.hintSteps.Length == 0))
                room.hintSteps = PlaceholderHints();
        }

        static void ApplyGuardian(RoomRow row, GuardianDefinition guardian)
        {
            guardian.id = "G-" + row.Id;
            guardian.kind = GuardianKindOf(row.Ring);
            guardian.wantsKind = WantKindOf(row);
        }

        // Yer tutucu: köpek önce bekçiye bakar, sonra burnunu dioramaya yöneltir. Hedefler odanın
        // bulmacası kurulunca elle değiştirilir; yeniden üretim dolu hintSteps'e dokunmaz.
        static HintStepDef[] PlaceholderHints() => new[]
        {
            new HintStepDef { cue = HintCue.LookAt, targetId = "GuardianPoint" },
            new HintStepDef { cue = HintCue.PointNose, targetId = "Diorama" },
        };

        static GuardianKind GuardianKindOf(RingId ring)
        {
            switch (ring)
            {
                case RingId.Toprak: return GuardianKind.Animal;
                case RingId.Su: return GuardianKind.Child;
                case RingId.Nefes: return GuardianKind.Elder;
                case RingId.Golge: return GuardianKind.Self;
                case RingId.Ayna: return GuardianKind.Reflection;
                default: return GuardianKind.None;
            }
        }

        static WantKind WantKindOf(RoomRow row)
        {
            switch (row.Ring)
            {
                case RingId.Toprak: return WantKind.Item;
                case RingId.Su: return WantKind.Habit;
                case RingId.Nefes: return WantKind.Anger;
                case RingId.Golge: return WantKind.Fear;
                case RingId.Ayna: return WantKind.Memory;
                case RingId.Sessizlik: return row.Index == 1 ? WantKind.Name : WantKind.Silence;
                default: return WantKind.Nothing;
            }
        }

        // Alanlar varlık oluşturulmadan önce yazılır; böylece OnValidate boş id görmez.
        static T Upsert<T>(string assetPath, Action<T> apply, out bool created) where T : ScriptableObject
        {
            var asset = AssetDatabase.LoadAssetAtPath<T>(assetPath);
            created = asset == null;
            if (created)
            {
                asset = ScriptableObject.CreateInstance<T>();
                apply(asset);
                AssetDatabase.CreateAsset(asset, assetPath);
            }
            else
            {
                apply(asset);
                EditorUtility.SetDirty(asset);
            }
            return asset;
        }

        static void EnsureFolder(string folder)
        {
            if (AssetDatabase.IsValidFolder(folder)) return;
            string parent = Path.GetDirectoryName(folder).Replace('\\', '/');
            EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, Path.GetFileName(folder));
        }
    }
}
