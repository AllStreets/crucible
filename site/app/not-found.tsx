import Link from "next/link";

export default function NotFound() {
  return (
    <div className="sheet page" style={{ minHeight: "50vh" }}>
      <div className="eyebrow"><span className="label">No such row</span></div>
      <h1 style={{ maxWidth: "18ch" }}>Nothing in the record has that address.</h1>
      <p className="lede">Every page here is generated from a row in the dataset. If a run, an agent, or a pair had this address, it would exist. <Link href="/">Back to the record</Link>, or press <span className="kbd">cmd</span> <span className="kbd">K</span>.</p>
    </div>
  );
}
