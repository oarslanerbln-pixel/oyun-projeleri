using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text.RegularExpressions;
using KirkOda.Core;

namespace KirkOda.Tooling
{
    /// <summary>
    /// Senaryo kilidindeki bir oda satırı (docs/01-senaryo-kilidi/kirk-oda.md). Yalnız tablonun söylediği:
    /// diorama, ses, kamera ve ipucu hedefleri elle kurulur.
    /// </summary>
    public sealed class RoomRow
    {
        public readonly string Id;            // R{n}-{nn}
        public readonly RingId Ring;
        public readonly int Index;            // halka içinde 1..roomCount
        public readonly int Number;           // kırk içindeki yer, 1..40
        public readonly string Puzzle;        // "Bulmaca" sütunu; iki gelişli odada iki cümle
        public readonly string Variable;      // "Değiştirilen değişken"
        public readonly string Guardian;      // "Bekçi"
        public readonly string Wants;         // "İstediği …"
        public readonly HalKind Hal;
        public readonly int EstimatedMinutes; // iki gelişli odada gelişlerin toplamı
        public readonly int Visits;

        public RoomRow(string id, RingId ring, int index, int number, string puzzle, string variable,
            string guardian, string wants, HalKind hal, int estimatedMinutes, int visits)
        {
            Id = id; Ring = ring; Index = index; Number = number; Puzzle = puzzle; Variable = variable;
            Guardian = guardian; Wants = wants; Hal = hal; EstimatedMinutes = estimatedMinutes; Visits = visits;
        }
    }

    /// <summary>
    /// kirk-oda.md tablolarını okur. UnityEngine'e bağlı değildir: aynı kod Editor menüsünde ve
    /// tools/core-tests altında dotnet ile koşar. Tablo ile kimlik sözleşmesi (RingCatalog) çelişirse
    /// sessizce düzeltmez, satır numarasıyla FormatException atar.
    /// </summary>
    public static class RoomTableParser
    {
        public const string RelativePath = "docs/01-senaryo-kilidi/kirk-oda.md";

        /// <summary>K-04: Toprak ve Su odaları en çok 3 dakika.</summary>
        public const int OuterRingMaxMinutes = 3;

        static readonly Regex RingHeading = new Regex(@"^## Halka (\d) — ");
        static readonly Regex RoomCell = new Regex(@"^(R\d-\d\d) \((\d+)\)(.*)$");
        static readonly Regex Minutes = new Regex(@"(\d+)(?:–(\d+))? dk");

        /// <summary>startDirectory'den yukarı çıkarak tabloyu arar; bulamazsa null.</summary>
        public static string LocateTable(string startDirectory)
        {
            for (var dir = new DirectoryInfo(startDirectory); dir != null; dir = dir.Parent)
            {
                string candidate = Path.Combine(dir.FullName, RelativePath);
                if (File.Exists(candidate)) return candidate;
            }
            return null;
        }

        /// <summary>Kırk odanın hepsi, id sırasıyla. Eksik ya da fazla oda FormatException'dır.</summary>
        public static IReadOnlyDictionary<string, RoomRow> Parse(string markdown)
        {
            var rows = new SortedDictionary<string, RoomRow>(StringComparer.Ordinal);
            var section = RingId.None;
            int sectionMinutes = 0;
            string[] header = null;

            var lines = markdown.Replace("\r\n", "\n").Split('\n');
            for (int n = 0; n < lines.Length; n++)
            {
                string line = lines[n].Trim();
                if (line.StartsWith("#", StringComparison.Ordinal))
                {
                    var h = RingHeading.Match(line);
                    section = h.Success ? (RingId)int.Parse(h.Groups[1].Value, CultureInfo.InvariantCulture) : RingId.None;
                    sectionMinutes = section == RingId.None ? 0 : MidMinutes(line);
                    header = null;
                    continue;
                }
                if (section == RingId.None || !line.StartsWith("|", StringComparison.Ordinal)) continue;

                string[] cells = SplitRow(line);
                if (cells[0] == "Oda") { header = cells; continue; }
                if (header == null || cells[0].StartsWith("---", StringComparison.Ordinal)) continue;

                var row = ParseRow(cells, header, section, sectionMinutes, n + 1);
                if (rows.TryGetValue(row.Id, out var first))
                    rows[row.Id] = MergeVisits(first, row, n + 1);
                else
                    rows.Add(row.Id, row);
            }

            Validate(rows);
            return rows;
        }

        static RoomRow ParseRow(string[] cells, string[] header, RingId section, int sectionMinutes, int lineNo)
        {
            var m = RoomCell.Match(cells[0]);
            if (!m.Success) throw Error(lineNo, $"oda hücresi okunamadı: '{cells[0]}'");
            string id = m.Groups[1].Value;
            if (!RingCatalog.TryParseRoomId(id, out var ring, out var index))
                throw Error(lineNo, $"'{id}' geçerli bir oda kimliği değil");
            if (ring != section)
                throw Error(lineNo, $"'{id}' {section} halkasının tablosunda");

            int number = int.Parse(m.Groups[2].Value, CultureInfo.InvariantCulture);
            var own = Minutes.Match(m.Groups[3].Value);
            int minutes = own.Success ? MidMinutes(own) : sectionMinutes;
            if (ring == RingId.Toprak || ring == RingId.Su) minutes = Math.Min(minutes, OuterRingMaxMinutes);

            int hal = Column(header, "Hâl");
            return new RoomRow(id, ring, index, number,
                puzzle: Cell(cells, 1),
                variable: Cell(cells, Column(header, "Değiştirilen")),
                guardian: Cell(cells, Column(header, "Bekçi")),
                wants: Cell(cells, Column(header, "İstediği")),
                hal: hal < 0 ? HalKind.None : ParseHal(Cell(cells, hal), lineNo),
                estimatedMinutes: minutes,
                visits: 1);
        }

        // R6-01 iki kez gezilir (ilk geliş kırk yılı atlatır, ikinci geliş adı ister): tek varlık, iki cümle.
        static RoomRow MergeVisits(RoomRow a, RoomRow b, int lineNo)
        {
            if (a.Number != b.Number) throw Error(lineNo, $"'{a.Id}' iki farklı sırada: {a.Number} ve {b.Number}");
            return new RoomRow(a.Id, a.Ring, a.Index, a.Number,
                a.Puzzle + "\n\n" + b.Puzzle, a.Variable + "\n\n" + b.Variable,
                a.Guardian, a.Wants + "\n\n" + b.Wants, a.Hal,
                a.EstimatedMinutes + b.EstimatedMinutes, a.Visits + b.Visits);
        }

        static HalKind ParseHal(string cell, int lineNo)
        {
            if (cell.Length == 0 || cell.StartsWith("—", StringComparison.Ordinal)) return HalKind.None;
            if (cell.StartsWith("Duvar titrer", StringComparison.Ordinal)) return HalKind.WallPass;
            if (cell.Contains("kasabayla eşitlenir")) return HalKind.TimeMatch;
            if (cell.StartsWith("Bekçi bir kez görülür", StringComparison.Ordinal)) return HalKind.GuardianSeen;
            throw Error(lineNo, $"bilinmeyen hâl: '{cell}'");
        }

        static void Validate(SortedDictionary<string, RoomRow> rows)
        {
            int expectedNumber = 0;
            for (int r = 1; r <= RingCatalog.RingCount; r++)
            {
                var ring = (RingId)r;
                for (int i = 1; i <= RingCatalog.RoomCount(ring); i++)
                {
                    string id = RingCatalog.RoomId(ring, i);
                    expectedNumber++;
                    if (!rows.TryGetValue(id, out var row))
                        throw new FormatException($"kirk-oda.md: {id} tabloda yok");
                    if (row.Number != expectedNumber)
                        throw new FormatException($"kirk-oda.md: {id} kırk içinde {expectedNumber}. olmalı, tabloda {row.Number}");
                }
            }
            if (rows.Count != RingCatalog.TotalRooms)
                throw new FormatException($"kirk-oda.md: {rows.Count} oda okundu, {RingCatalog.TotalRooms} bekleniyordu");
        }

        static string[] SplitRow(string line)
        {
            string inner = line.Trim('|');
            string[] cells = inner.Split('|');
            for (int i = 0; i < cells.Length; i++) cells[i] = cells[i].Trim();
            return cells;
        }

        static int Column(string[] header, string prefix)
        {
            for (int i = 0; i < header.Length; i++)
                if (header[i].StartsWith(prefix, StringComparison.Ordinal)) return i;
            return -1;
        }

        static string Cell(string[] cells, int column) =>
            column >= 0 && column < cells.Length ? cells[column] : string.Empty;

        static int MidMinutes(string text)
        {
            var m = Minutes.Match(text);
            return m.Success ? MidMinutes(m) : 0;
        }

        static int MidMinutes(Match m)
        {
            int lo = int.Parse(m.Groups[1].Value, CultureInfo.InvariantCulture);
            int hi = m.Groups[2].Success ? int.Parse(m.Groups[2].Value, CultureInfo.InvariantCulture) : lo;
            return (lo + hi) / 2;
        }

        static FormatException Error(int lineNo, string message) =>
            new FormatException($"kirk-oda.md:{lineNo}: {message}");
    }
}
