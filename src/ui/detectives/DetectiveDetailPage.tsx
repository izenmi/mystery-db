import { Link, useParams } from "react-router-dom";
import { getDetective } from "../../data/manifest";
import { useAsyncData } from "../common/useAsyncData";
import { Loading, ErrorState, EmptyState } from "../common/Status";
import { WorkCard } from "../common/WorkCard";
import { BASE_PATH, SITE_NAME, breadcrumbJsonLd, useSeo } from "../common/useSeo";
import { useWorkFilter } from "../common/useWorkFilter";

/** 既定の並びは発表順(古い順)。「どれから読めばいいか」がこのページの用なので、
 *  ここだけ defaultSort を year-asc にしている。絞り込みは他の一覧ページと揃えて出す。 */
export function DetectiveDetailPage() {
  const { id } = useParams<{ id: string }>();
  const state = useAsyncData(() => getDetective(id!), [id]);
  const detective = state.status === "ready" ? state.data : undefined;
  const { sorted, controls, hasActiveFilters } = useWorkFilter(detective?.works, "year-asc");

  useSeo({
    title: detective?.name,
    description: detective
      ? `名探偵「${detective.name}」(${detective.creatorAuthorName})の登場作品${detective.workCount}件を発表順に紹介。${detective.description}`.slice(
          0,
          160
        )
      : undefined,
    jsonLd: detective
      ? [
          {
            "@context": "https://schema.org",
            "@type": "Person",
            name: detective.name,
            description: detective.description,
            ...(detective.occupation && { jobTitle: detective.occupation }),
            ...(detective.externalLinks.wikipediaUrl && { sameAs: [detective.externalLinks.wikipediaUrl] }),
          },
          breadcrumbJsonLd([
            { name: SITE_NAME, path: BASE_PATH },
            { name: "探偵一覧", path: `${BASE_PATH}detectives` },
            { name: detective.name, path: `${BASE_PATH}detectives/${id}` },
          ]),
        ]
      : undefined,
  });

  return (
    <div className="page">
      {state.status === "loading" && <Loading />}
      {state.status === "error" && <ErrorState error={state.error} />}
      {state.status === "ready" && !state.data && <EmptyState text="見つかりませんでした。" />}
      {state.status === "ready" && state.data && (
        <>
          <h1>{state.data.name}</h1>
          <p className="page-subtitle">
            生みの親: <Link to={`/authors/${state.data.creatorAuthorId}`}>{state.data.creatorAuthorName}</Link>
            {state.data.occupation && ` / ${state.data.occupation}`}
            {" / "}
            {state.data.workCount}作品
          </p>
          <p>{state.data.description}</p>
          {state.data.firstAppearanceWorkId && (
            <p className="page-subtitle">
              初登場: <Link to={`/works/${state.data.firstAppearanceWorkId}`}>
                {state.data.works.find((w) => w.id === state.data!.firstAppearanceWorkId)?.title ??
                  state.data.firstAppearanceWorkId}
              </Link>
            </p>
          )}
          {state.data.externalLinks.wikipediaUrl && (
            <p>
              <a href={state.data.externalLinks.wikipediaUrl} target="_blank" rel="noreferrer">
                Wikipediaで見る
              </a>
            </p>
          )}
          <h2 className="home-section__heading font-display">登場作品</h2>
          {controls}
          {hasActiveFilters && (
            <p className="page-subtitle">
              絞り込み結果 {sorted.length}件 / 全{state.data.works.length}件
            </p>
          )}
          {sorted.length === 0 && <EmptyState text="該当する作品がありません。" />}
          <div className="work-grid">
            {sorted.map((w) => (
              <WorkCard work={w} key={w.id} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
