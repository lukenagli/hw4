import { Link } from 'react-router-dom'
import { Pennant } from '../components/Brand'

const VALUES = [
  {
    title: 'Officially licensed',
    body: 'Every design we sell carries authentic Yale marks, so what you wear is the real thing.',
  },
  {
    title: 'Made for the whole community',
    body: 'Students, alumni, faculty, parents, grandparents and fans all find something to wear here.',
  },
  {
    title: 'Local to New Haven',
    body: 'We are a short walk from Old Campus. Stop by, try a size and say hello.',
  },
]

export default function About() {
  return (
    <>
      <section className="page-hero felt">
        <div className="container">
          <Pennant label="About the shop" />
          <h1>Yale spirit, right on Broadway.</h1>
        </div>
      </section>

      <section className="container section about">
        <div className="about-copy">
          <p className="lead">
            Campus Customs is a Yale apparel shop based in New Haven. We make it easy to show where you
            belong, whether that's a residential college, a graduate school, a varsity team or simply the
            Bulldogs.
          </p>
          <p>
            Our shelves are stocked with everyday pieces: soft hoodies and crewnecks for cold walks across
            campus, tees for game days, quarter-zips that work in the library or the office, and warm fleece
            for New England winters. Many come in college crests and team designs, so you can be specific
            about your corner of Yale.
          </p>
          <p>
            We also think family counts. Parents, grandparents, siblings and cousins have their own designs,
            because cheering on a Yalie is a team sport too.
          </p>
          <p>
            Come see us at <strong>57 Broadway, New Haven, CT 06511</strong>, or browse the full collection
            online. Our shop assistant in the corner of every page can help you find the right piece.
          </p>
          <Link to="/products" className="btn btn-primary">
            Shop the collection
          </Link>
        </div>

        <div className="values">
          {VALUES.map((v) => (
            <div key={v.title} className="value">
              <h3>{v.title}</h3>
              <p>{v.body}</p>
            </div>
          ))}
        </div>
      </section>
    </>
  )
}
