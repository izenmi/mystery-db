import { Link, useParams } from "react-router-dom";
import { getDetective } from "../../data/manifest";
import { useAsyncData } from "../common/useAsyncData";
import { Loading, ErrorState, EmptyState } from "../common/Status";
import { WorkCard } from "../common/WorkCard";
import { BASE_PATH, SITE_NAME, breadcrumbJsonLd, useSeo } from "../common/useSeo";

/** Unlike every other cross-reference page on the site, the case list here is NOT re-sortable:
 *  it is always publication order, because "which one do I read first?" is the question this
 *  page exists to answer. generate-manifest.mjs already emits `works` in that order. */
export function DetectiveDetailPage() {
  const { id } = useParams<{ id: string }>();
  const state = useAsyncData(() => getDetective(id!), [id]);
  const detective = state.status === "ready" ? state.data : undefined;

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
          <h2 className="home-section__heading font-display">登場作品(発表順)</h2>
          <div className="work-grid">
            {state.data.works.map((w) => (
              <WorkCard work={w} key={w.id} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
