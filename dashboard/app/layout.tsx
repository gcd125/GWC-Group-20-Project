import type {Metadata} from 'next';
import './globals.css';
export const metadata:Metadata={title:'GWC Insights — Your community, in focus',description:'Private Girls Who Code @ UCF membership, event, and attendance analytics.'};
export default function Layout({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>}
