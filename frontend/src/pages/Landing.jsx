import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, BarChart2, Zap, Brain, UploadCloud, CheckCircle, Database, Lock, Globe, FileText } from 'lucide-react';

const Landing = () => {
    return (
        <div style={{
            minHeight: '100vh',
            background: 'var(--background)',
            color: 'var(--text-primary)',
            overflowX: 'hidden',
            fontFamily: 'var(--font-sans)'
        }}>

            {/* --- BACKGROUND EFFECTS --- */}
            <div className="bg-glow-top" style={{
                position: 'absolute', top: '-10%', left: '25%', width: '50vw', height: '50vw',
                background: 'radial-gradient(circle, var(--primary-glow) 0%, transparent 60%)',
                filter: 'blur(120px)', opacity: 0.4, zIndex: 0
            }} />

            {/* --- NAVBAR --- */}
            <nav style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '24px 48px',
                position: 'relative', zIndex: 50, backdropFilter: 'blur(10px)', borderBottom: '1px solid rgba(255,255,255,0.05)'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '1.5rem', fontWeight: 'bold', letterSpacing: '-0.5px' }}>
                    <div style={{
                        width: '40px', height: '40px', background: 'linear-gradient(135deg, #FF6B6B, #7C3AED)',
                        borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 20px rgba(124, 58, 237, 0.4)'
                    }}>
                        <BarChart2 color="white" size={24} />
                    </div>
                    <span>One Click <span style={{ color: 'var(--primary)' }}>Analysis</span></span>
                </div>
                <div style={{ display: 'flex', gap: '30px', alignItems: 'center' }}>
                    {['Analysis', 'Solutions', 'Resources', 'Pricing'].map(item => (
                        <a key={item} href={`#${item.toLowerCase()}`} style={{
                            textDecoration: 'none', color: 'var(--text-secondary)', fontSize: '0.95rem', fontWeight: '500', transition: 'color 0.2s'
                        }} className="nav-link">{item}</a>
                    ))}
                    <Link to="/login">
                        <button className="btn-glow" style={{
                            padding: '10px 24px', background: 'linear-gradient(90deg, #FF9966, #FF5E62)', color: 'white',
                            border: 'none', borderRadius: '30px', fontWeight: 'bold', cursor: 'pointer', boxShadow: '0 4px 15px rgba(255, 94, 98, 0.4)'
                        }}>My Account</button>
                    </Link>
                </div>
            </nav>

            {/* --- HERO SECTION --- */}
            <section style={{ padding: '80px 20px', textAlign: 'center', position: 'relative', zIndex: 10 }}>

                <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }}>
                    <h1 style={{
                        fontSize: '4.5rem', fontWeight: '800', lineHeight: 1.1, marginBottom: '1.5rem',
                        background: 'linear-gradient(to bottom, #ffffff, #a5b4fc)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'
                    }}>
                        Unleash the Power of <br /> <span style={{ color: 'var(--primary)' }}>Your Data</span>
                    </h1>
                    <p style={{ fontSize: '1.2rem', color: 'var(--text-secondary)', maxWidth: '600px', margin: '0 auto 60px auto' }}>
                        Discover actionable insights to drive business growth with our AI-powered analytics platform.
                    </p>
                </motion.div>

                {/* --- SPARKLING ANIMATION & BUTTONS --- */}
                <div style={{ position: 'relative', display: 'inline-block', marginBottom: '60px' }}>
                    {/* The "Picture" / Animation Area */}
                    <div style={{
                        width: '600px', height: '300px', margin: '0 auto', position: 'relative',
                        background: 'rgba(255,255,255,0.01)', borderRadius: '20px', overflow: 'hidden'
                    }}>
                        {/* Fiber Optic Lines */}
                        {[...Array(20)].map((_, i) => (
                            <SparklingLine key={i} delay={i * 0.1} left={`${5 + i * 5}%`} />
                        ))}

                        {/* Central Glow */}
                        <div style={{
                            position: 'absolute', bottom: 0, left: '50%', transform: 'translateX(-50%)',
                            width: '300px', height: '150px', background: 'radial-gradient(ellipse at bottom, var(--primary) 0%, transparent 70%)',
                            filter: 'blur(60px)', opacity: 0.6
                        }} />
                    </div>

                    {/* Buttons centered below animation */}
                    <div style={{ display: 'flex', gap: '20px', justifyContent: 'center', marginTop: '-40px', position: 'relative', zIndex: 20 }}>
                        <Link to="/login?mode=signup">
                            <motion.button whileHover={{ scale: 1.05 }} style={{
                                padding: '18px 40px', fontSize: '1.1rem', fontWeight: 'bold',
                                background: 'linear-gradient(90deg, #8B5CF6, #EC4899)', color: 'white',
                                border: 'none', borderRadius: '50px', cursor: 'pointer',
                                boxShadow: '0 0 30px rgba(139, 92, 246, 0.5)'
                            }}>
                                Get Free Consultation
                            </motion.button>
                        </Link>
                        <Link to="/login">
                            <motion.button whileHover={{ scale: 1.05 }} style={{
                                padding: '18px 40px', fontSize: '1.1rem', fontWeight: 'bold',
                                background: 'rgba(255,255,255,0.1)', color: 'white', border: '1px solid rgba(255,255,255,0.2)',
                                borderRadius: '50px', cursor: 'pointer', backdropFilter: 'blur(10px)'
                            }}>
                                Get Your Report
                            </motion.button>
                        </Link>
                    </div>
                </div>
            </section>

            {/* --- FEATURES GRID (Trusted Partner) --- */}
            <section id="analysis" style={{ padding: '100px 40px', background: 'linear-gradient(to bottom, #030014, #0f172a)' }}>
                <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
                    <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}>
                        <h2 style={{ fontSize: '2.5rem', fontWeight: 'bold', marginBottom: '60px' }}>
                            Your Trusted Partner in <br /> <span style={{ color: '#F472B6' }}>Data-Driven Success</span>
                        </h2>
                    </motion.div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '30px' }}>
                        <FeatureCard
                            title="Comprehensive Analysis"
                            desc="Traffic and revenue tools give you digital solutions that give insights across the value of your website content."
                            gradient="linear-gradient(180deg, rgba(139, 92, 246, 0.1), transparent)"
                            icon={<Database color="#A78BFA" size={32} />}
                        />
                        <FeatureCard
                            title="Flexible Reporting"
                            desc="Remove the complexity of analytics to create custom reports that adapt to your unique publishing needs."
                            gradient="linear-gradient(180deg, rgba(52, 211, 153, 0.1), transparent)"
                            icon={<FileText color="#34D399" size={32} />}
                        />
                        <FeatureCard
                            title="Predictive Insights"
                            desc="Leverage advanced AI that acts like a true data nerd, anticipating trends and traffic opportunities."
                            gradient="linear-gradient(180deg, rgba(251, 191, 36, 0.1), transparent)"
                            icon={<Brain color="#FBBF24" size={32} />}
                        />
                    </div>
                </div>
            </section>

            {/* --- DYNAMIC CAPABILITIES (Strategy) --- */}
            <section id="solutions" style={{ padding: '100px 40px' }}>
                <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', alignItems: 'center', gap: '60px' }}>
                    <div style={{ flex: 1 }}>
                        <h2 style={{ fontSize: '3rem', fontWeight: 'bold', lineHeight: 1.2, marginBottom: '30px' }}>
                            Dynamic reports & <br />
                            <span style={{ color: '#F472B6' }}>interactive capabilities</span>
                        </h2>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                            <Capability icon={<Zap size={24} color="#A78BFA" />} title="SEO Performance" desc="Understand which topics are already generating the most revenue and ROI." />
                            <Capability icon={<Globe size={24} color="#FBBF24" />} title="Audience Priorities" desc="Discover in granular detail how your audience interacts with your content." />
                        </div>
                        <Link to="/login">
                            <button style={{
                                marginTop: '40px', padding: '14px 30px', background: '#8B5CF6', color: 'white',
                                border: 'none', borderRadius: '30px', fontWeight: 'bold', cursor: 'pointer'
                            }}>See Live Report</button>
                        </Link>
                    </div>
                    <div style={{ flex: 1, position: 'relative' }}>
                        {/* Isometric Illustration Mockup */}
                        <div style={{
                            width: '100%', height: '400px', background: 'linear-gradient(135deg, #1e293b, #0f172a)',
                            borderRadius: '20px', border: '1px solid rgba(255,255,255,0.1)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            transform: 'perspective(1000px) rotateY(-10deg) rotateX(5deg)',
                            boxShadow: '50px 50px 100px rgba(0,0,0,0.5)'
                        }}>
                            <BarChart2 size={120} color="rgba(255,255,255,0.05)" />
                        </div>
                    </div>
                </div>
            </section>

            {/* --- TAILORED STRATEGIES --- */}
            <section style={{ padding: '100px 40px', background: '#020617' }}>
                <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
                    <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}>
                        <h2 style={{ fontSize: '3rem', fontWeight: 'bold', lineHeight: 1.2, marginBottom: '60px', textAlign: 'center' }}>
                            Tailored Data-Driven Strategies & <br />
                            <span style={{ color: '#F472B6' }}>Empowering Your Business with Analytics</span>
                        </h2>
                    </motion.div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '30px' }}>
                        <StrategyCard
                            title="Data Ingestion and Preparation"
                            desc="Our data ingestion and preparation services involve collecting data from diverse sources, cleaning, and standardization."
                            icon={<Database size={40} color="#2DD4BF" />}
                            gradient="linear-gradient(135deg, rgba(45, 212, 191, 0.1), transparent)"
                            border="1px solid #2DD4BF"
                        />
                        <StrategyCard
                            title="Analysis and Visualization"
                            desc="Our analysis services include Exploratory data analysis (EDA), advanced analytics techniques, and customized automated reporting."
                            icon={<BarChart2 size={40} color="#FACC15" />}
                            gradient="linear-gradient(135deg, rgba(250, 204, 21, 0.1), transparent)"
                            border="1px solid #FACC15"
                        />
                        <StrategyCard
                            title="Predictive Analytics"
                            desc="Our predictive analytics services leverage machine learning to forecast future trends, identify potential risks, and optimize decision-making."
                            icon={<Brain size={40} color="#A855F7" />}
                            gradient="linear-gradient(135deg, rgba(168, 85, 247, 0.1), transparent)"
                            border="1px solid #A855F7"
                        />
                        <StrategyCard
                            title="Custom Solutions"
                            desc="Our team of experts can tailor our services to meet your unique needs, including industry-specific solutions and compliance."
                            icon={<Lock size={40} color="#4ADE80" />}
                            gradient="linear-gradient(135deg, rgba(74, 222, 128, 0.1), transparent)"
                            border="1px solid #4ADE80"
                        />
                    </div>
                </div>
            </section>

            {/* --- PRICING SECTION --- */}
            <section id="pricing" style={{ padding: '100px 40px', background: '#020617' }}>
                <div style={{ maxWidth: '1200px', margin: '0 auto', textAlign: 'center' }}>
                    <h2 style={{ fontSize: '3rem', fontWeight: 'bold', marginBottom: '80px' }}>
                        Transparent <span style={{ color: '#F472B6' }}>Pricing</span>
                    </h2>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '30px', textAlign: 'left' }}>
                        <PricingCard
                            title="Essential Plan"
                            price="1,00,000"
                            desc="Perfect for startups."
                            features={['10GB Storage', 'Basic Analytics', 'Email Support']}
                            gradient="linear-gradient(135deg, #4f46e5, #9333ea)"
                        />
                        <PricingCard
                            title="Professional Plan"
                            price="1,40,000"
                            desc="For growing teams."
                            features={['50GB Storage', 'Advanced AutoML', 'Priority Support', 'API Access']}
                            isPopular
                            gradient="linear-gradient(135deg, #ec4899, #f43f5e)"
                        />
                        <PricingCard
                            title="Enterprise Plan"
                            price="2,10,000"
                            desc="For large organizations."
                            features={['Unlimited Storage', 'Custom Models', 'Dedicated Manager', 'SSO']}
                            gradient="linear-gradient(135deg, #f59e0b, #d97706)"
                        />
                    </div>
                </div>
            </section>

            {/* --- CTA FOOTER --- */}
            <section style={{ padding: '80px 20px', textAlign: 'center', position: 'relative', overflow: 'hidden' }}>
                <div style={{
                    maxWidth: '900px', margin: '0 auto', background: 'rgba(255,255,255,0.05)',
                    borderRadius: '30px', padding: '60px', border: '1px solid rgba(255,255,255,0.1)'
                }}>
                    <h2 style={{ fontSize: '2.5rem', fontWeight: 'bold', marginBottom: '20px' }}>Ready to Unlock the Power of Your Data?</h2>
                    <p style={{ color: 'var(--text-secondary)', marginBottom: '40px' }}>Start your data-driven journey today with our Free Consultation.</p>
                    <Link to="/login?mode=signup">
                        <button style={{
                            padding: '16px 40px', fontSize: '1.1rem', fontWeight: 'bold',
                            background: 'linear-gradient(90deg, #8B5CF6, #EC4899)', color: 'white',
                            border: 'none', borderRadius: '50px', cursor: 'pointer',
                            boxShadow: '0 0 30px rgba(139, 92, 246, 0.5)'
                        }}>Get A Free Consultation</button>
                    </Link>
                </div>
            </section>

            {/* --- FOOTER --- */}
            <footer style={{ padding: '40px', borderTop: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'space-between', color: '#64748b' }}>
                <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontWeight: 'bold', color: 'white', marginBottom: '10px' }}>
                        <BarChart2 size={20} color="#F472B6" /> BigData
                    </div>
                    <p>google@mail.com | +1 234 5678 9010</p>
                </div>
                <div style={{ display: 'flex', gap: '40px' }}>
                    <div>
                        <h4 style={{ color: 'white', marginBottom: '10px' }}>Product</h4>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                            <span>Sign Up</span><span>Login</span><span>Security</span>
                        </div>
                    </div>
                    <div>
                        <h4 style={{ color: 'white', marginBottom: '10px' }}>Company</h4>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                            <span>About</span><span>Careers</span><span>Contact</span>
                        </div>
                    </div>
                </div>
            </footer>

        </div>
    );
};

// --- COMPONENTS ---

const SparklingLine = ({ delay, left }) => (
    <div style={{
        position: 'absolute', bottom: 0, left: left, width: '1px', height: '100%',
        background: 'rgba(255,255,255,0.1)', overflow: 'hidden'
    }}>
        <motion.div
            animate={{ y: [300, -300], opacity: [0, 1, 0] }}
            transition={{ duration: 2, repeat: Infinity, delay: delay, ease: "linear" }}
            style={{
                width: '4px', height: '40px', background: 'linear-gradient(to top, transparent, var(--primary), white)',
                borderRadius: '4px', marginLeft: '-1.5px'
            }}
        />
    </div>
);

const FeatureCard = ({ title, desc, icon, gradient }) => (
    <motion.div whileHover={{ y: -10 }} style={{
        padding: '30px', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)',
        borderRadius: '20px', position: 'relative', overflow: 'hidden'
    }}>
        <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', background: gradient, opacity: 0.5 }} />
        <div style={{ marginBottom: '20px', position: 'relative', zIndex: 1 }}>{icon}</div>
        <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', marginBottom: '10px', position: 'relative', zIndex: 1 }}>{title}</h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.6', position: 'relative', zIndex: 1 }}>{desc}</p>
    </motion.div>
);

const Capability = ({ icon, title, desc }) => (
    <div style={{ display: 'flex', gap: '15px', alignItems: 'flex-start' }}>
        <div style={{ padding: '10px', background: 'rgba(255,255,255,0.05)', borderRadius: '10px' }}>{icon}</div>
        <div>
            <h4 style={{ fontSize: '1.1rem', fontWeight: 'bold', marginBottom: '5px' }}>{title}</h4>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{desc}</p>
        </div>
    </div>
);

const StrategyCard = ({ title, desc, icon, gradient, border }) => (
    <motion.div whileHover={{ y: -5 }} style={{
        padding: '40px', background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(255,255,255,0.1)', borderLeft: `4px solid ${border.split(' ')[2]}`,
        borderRadius: '20px', display: 'flex', gap: '20px',
        alignItems: 'flex-start'
    }}>
        <div style={{ padding: '15px', background: gradient, borderRadius: '12px', flexShrink: 0 }}>
            {icon}
        </div>
        <div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', marginBottom: '10px' }}>{title}</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.6' }}>{desc}</p>
        </div>
    </motion.div>
);

const PricingCard = ({ title, price, desc, features, isPopular, gradient }) => (
    <motion.div whileHover={{ scale: 1.02 }} style={{
        background: 'rgba(255,255,255,0.03)', border: isPopular ? '1px solid #EC4899' : '1px solid rgba(255,255,255,0.1)',
        borderRadius: '24px', padding: '40px', position: 'relative', overflow: 'hidden'
    }}>
        {isPopular && <div style={{
            position: 'absolute', top: 0, right: 0, background: '#EC4899', color: 'white',
            padding: '5px 15px', fontSize: '0.8rem', fontWeight: 'bold', borderBottomLeftRadius: '10px'
        }}>POPULAR</div>}

        <div style={{ width: '50px', height: '50px', borderRadius: '50%', background: gradient, marginBottom: '20px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Zap color="white" size={24} />
        </div>

        <h3 style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>{title}</h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '20px' }}>{desc}</p>

        <div style={{ fontSize: '2.5rem', fontWeight: 'bold', marginBottom: '30px' }}>
            ₹{price} <span style={{ fontSize: '1rem', color: 'var(--text-muted)', fontWeight: 'normal' }}>/month</span>
        </div>

        <ul style={{ listStyle: 'none', padding: 0, marginBottom: '30px', color: 'var(--text-secondary)' }}>
            {features.map((f, i) => (
                <li key={i} style={{ marginBottom: '10px', display: 'flex', gap: '10px', alignItems: 'center' }}>
                    <CheckCircle size={16} color="var(--success)" /> {f}
                </li>
            ))}
        </ul>

        <Link to="/login?mode=signup">
            <button style={{
                width: '100%', padding: '14px', background: isPopular ? '#EC4899' : 'rgba(255,255,255,0.1)',
                border: 'none', borderRadius: '12px', color: 'white', fontWeight: 'bold', cursor: 'pointer'
            }}>
                Choose Plan
            </button>
        </Link>
    </motion.div>
);

export default Landing;
