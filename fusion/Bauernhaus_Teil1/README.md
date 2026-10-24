# Bauernhaus – Gebäudeteil 1 (Fusion-Skript)

Volumenmodell KG–DG inkl. Dach, Schleppgaube, Balkon, Treppen, Fenster und Türen,
abgeleitet aus den Grundrissen M 1:100 (nur Räume mit Kennung ①).

## Ausführen in Fusion
1. Ordner `Bauernhaus_Teil1/` nach *Utilities → Add-Ins → Scripts and Add-Ins → +* (Pfad hinzufügen).
2. Vorher unter *Einstellungen → Allgemein → Standard-Modellierungsausrichtung* **Z oben** wählen.
3. Skript ausführen → neues Dokument mit Komponenten `KG, EG, OG, DG, Dach, Trennwand, Gelaende`,
   je Komponente Körper nach Kategorie (Außenwände, Innenwände, Decke, Verglasung, …).

Die Geometrie wird über den `TemporaryBRepManager` aufgebaut (Basis-Features, damit es im parametrischen Modus läuft).

## Koordinaten
X = Plan rechts (Giebel x = 0, Gebäudetrennwand x = 7,82–8,56), Y = Nord (0) → Süd (13,195),
Z = 0 auf OKFF EG. Draufsicht entspricht der Planlage (Plan oben = Süden).

## Annahmen (Block `ANNAHMEN` im Skript)
Höhen sind im Grundriss nicht bemaßt. Angenommen: Geschosshöhe 2,75 m, Deckenstärke 0,30 m,
Dachneigung 40°, Kniestock 0,30 m, Gaubenneigung 15°, Brüstung 0,90 m, Fensterhöhen 1,20 bis 1,26 m,
KG-Gewölbe mit Kämpfer +1,00 m und Stich 1,20 m (Plan: mittlere Höhe 1,90 m).
Treppen sind als gerade Läufe vereinfacht (im Plan gewendelt am Antritt).

## Vorschau ohne Fusion
`python vorschau.py out/` baut dieselbe CSG mit `manifold3d`, exportiert GLB und rendert Schnitte.
