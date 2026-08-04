// ---- source data (public/data/source/*.json, hand-authored, committed) ----

export interface ExternalLinks {
  wikipediaUrl?: string;
  officialUrl?: string;
}

export interface AwardResult {
  awardId: string;
  year: number;
  result: string; // free text: "受賞" / "候補" / "第1位" など
}

export type WorkStatus = "completed" | "ongoing" | "unknown";

/** Domestic (Japanese) work vs. a translated foreign one. Drives the 国内/海外 filter and
 *  decides whether originalTitle/jpPublishedYear/translatorIds are expected. */
export type WorkOrigin = "jp" | "overseas";

export interface WorkSource {
  id: string;
  /** Japanese title. For translated works this is the 邦題, not the original title. */
  title: string;
  titleKana: string;
  authorIds: string[];
  /** Series detectives appearing in this work. Empty for 倒叙・サスペンス・イヤミス等,
   *  where no recurring sleuth carries the story. */
  detectiveIds: string[];
  /** Empty for `origin: "jp"`; required for `origin: "overseas"`. */
  translatorIds: string[];
  publisherId: string;
  themeIds: string[];
  /** Plain display text such as "加賀恭一郎シリーズ" — deliberately not an entity, since the
   *  detective axis already covers series browsing and many series have no fixed sleuth. */
  seriesName?: string;
  origin: WorkOrigin;
  /** Year the work was first published in its original language. Translated works therefore
   *  sort alongside Japanese ones on a single mystery-history timeline. */
  firstPublishedYear: number;
  /** Translated works only: year the first Japanese edition appeared. */
  jpPublishedYear?: number;
  /** Translated works only. */
  originalTitle?: string;
  status: WorkStatus;
  /** 1 (or absent) for the standalone novels that make up most of the catalogue. */
  volumeCount?: number;
  /** 150〜250 chars, written from scratch. Must never give away the culprit or the trick. */
  synopsis: string;
  awardResults?: AwardResult[];
  /** Adaptation status, verified against the work's Wikipedia article. Live-action film/TV
   *  dominate this genre, so they get their own flags alongside anime/manga. */
  mediaMix?: { movie?: boolean; drama?: boolean; anime?: boolean; comic?: boolean };
  externalLinks: ExternalLinks;
  sourceNote: string;
  updatedAt: string;
}

export interface AuthorSource {
  id: string;
  name: string;
  nameKana: string;
  description: string;
  birthYear?: number;
  externalLinks: ExternalLinks;
  sourceNote: string;
  updatedAt: string;
}

export type TranslatorSource = AuthorSource;

/** A recurring sleuth. The site's differentiator: every detective page lists their cases in
 *  publication order, which is the thing readers actually want when starting a series. */
export interface DetectiveSource {
  id: string;
  name: string;
  nameKana: string;
  /** The author who created them (id into authors.json). */
  creatorAuthorId: string;
  /** 私立探偵 / 警部 / 大学助教授 / 素人 など。 */
  occupation?: string;
  /** Character sketch. Must never give away the culprit or the trick of any of their cases. */
  description: string;
  firstAppearanceWorkId?: string;
  externalLinks: ExternalLinks;
  sourceNote: string;
  updatedAt: string;
}

export interface PublisherSource {
  id: string;
  name: string;
  nameKana: string;
  parentCompany?: string;
  description: string;
  foundedYear?: number;
  externalLinks: ExternalLinks;
  sourceNote: string;
  updatedAt: string;
}

export interface ThemeSource {
  id: string;
  name: string;
  description?: string;
  /** True when knowing the tag applies to a work is itself a clue to the solution (叙述トリック
   *  etc.). Such tags are hidden from work cards entirely and revealed on the detail page only
   *  behind an explicit click. Structural tags the blurb already advertises (密室・館もの・
   *  クローズドサークル・倒叙…) are NOT spoilers. */
  spoiler?: boolean;
}

export interface AwardSource {
  id: string;
  name: string;
  organizer: string;
  description: string;
  firstYear?: number;
  externalLinks: ExternalLinks;
  sourceNote: string;
  updatedAt: string;
}

// ---- generated data (public/data/generated/*.json, built by scripts/generate-manifest.mjs) ----

/** Denormalized work: source fields plus resolved names for direct rendering. */
export interface WorkGenerated extends WorkSource {
  authorNames: string[];
  detectiveNames: string[];
  translatorNames: string[];
  publisherName: string;
  themeNames: string[];
  /** Ids of this work's themes that carry `spoiler: true`, so WorkCard can drop them without
   *  having to fetch themes.json itself. */
  spoilerThemeIds: string[];
  awardSummaries: { awardId: string; awardName: string; year: number; result: string }[];
  /** Resolved at build time from public/data/source/covers-cache.json (see scripts/fetch-covers.mjs).
   *  Absent when no ISBN/cover could be matched — callers must fall back to the placeholder cover. */
  coverUrl?: string;
}

/** Shared shape for authors/translators/publishers list+detail pages. */
export interface PersonOrPublisherGenerated {
  id: string;
  name: string;
  nameKana: string;
  description: string;
  externalLinks: ExternalLinks;
  workCount: number;
  works: WorkGenerated[];
}

export interface DetectiveGenerated extends DetectiveSource {
  creatorAuthorName: string;
  workCount: number;
  /** Sorted by firstPublishedYear ascending — the reading order for the series. */
  works: WorkGenerated[];
}

export interface ThemeGenerated extends ThemeSource {
  workCount: number;
  works: WorkGenerated[];
}

export interface AwardWinner {
  workId: string;
  workTitle: string;
  year: number;
  result: string;
}

export interface AwardGenerated extends AwardSource {
  workCount: number;
  winners: AwardWinner[];
}

export interface Counts {
  works: number;
  authors: number;
  detectives: number;
  translators: number;
  publishers: number;
  themes: number;
  awards: number;
}
