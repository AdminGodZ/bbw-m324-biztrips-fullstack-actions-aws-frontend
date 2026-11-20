import "bootstrap/dist/css/bootstrap.min.css";

import "./App.css";
import Wishlist from "./components/Wishlist";
import TripList from "./components/TripList";
import Employees from "./components/Employees";
import VersionInfo from "./components/VersionInfo";
import {useWishlist} from "./components/wishlistContext.jsx";

export default function App() {
    return (
        <div className="container">
            <header className="container h3">
                RefCard 05 - Business Trips - Full Stack on AWS (ECR, ECS, RDS, S3) | Tim Held

            </header>
            <Wishlist/>
            <TripList/>
            <Employees/>
            <WishlistTest/>
            <footer>
                <VersionInfo/>
                only for educational purposes @BBW 2026
            </footer>
        </div>


    );
}

function WishlistTest() {
    const {wishlist} = useWishlist()
    return (
        <div className="container">
            <header className="container h3">Wishlist-Test</header>
            <ul className="list-unstyled">
                {wishlist.map((item) => {
                    return (
                        <li key={item.id}>
                            {item.id} - {item.title} {item.description}
                        </li>
                    );
                })}
            </ul>
        </div>
    );
}
