import { Link } from "react-router-dom";
import { getDetectives } from "../../data/manifest";
import { useAsyncData } from "../common/useAsyncData";
import { Loading, ErrorState } from "../common/Status";
import { useSeo } from "../common/useSeo";

/** Detectives get their own list rather than reusing EntityList, because "who created them"
 *  is the piece of context that makes an unfamiliar sleuth's name meaningful. */
export function DetectiveListPage() {
  const state = useAsyncData(getDetectives, []);

  useSeo({
    title: "探偵一覧",
    description:
      state.status === "ready"
        ? `推理小説のシリーズ探偵${state.data.length}人の一覧。探偵ごとに登場作品を発表順で辿れます。`
        : undefined,
  });

  return (
    <div className="page">
      <h1>探偵</h1>
      {state.status === "loading" && <Loading />}
      {state.status === "error" && <ErrorState error={state.error} />}
      {state.status === "ready" && (
        <>
          <p className="page-subtitle">{state.data.length}人</p>
          <ul className="entity-list">
            {state.data.map((d) => (
              <li className="entity-list__item" key={d.id}>
                <Link to={`/detectives/${d.id}`}>
                  <span>
                    {d.name}
                    <span className="entity-list__note">
                      {d.creatorAuthorName}
                      {d.occupation && ` / ${d.occupation}`}
                    </span>
                  </span>
                  <span className="entity-list__count">{d.workCount}</span>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
