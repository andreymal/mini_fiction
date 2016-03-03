<?xml version="1.0"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns="http://www.gribuser.ru/xml/fictionbook/2.0"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:re="http://exslt.org/regular-expressions"
    extension-element-prefixes="re">
    
    <xsl:import href="fb2-description.xslt"/>
    
<xsl:template match="/html">
    <FictionBook xmlns:xlink="http://www.w3.org/1999/xlink">
        <xsl:call-template name="create-fb2-description">
            <xsl:with-param name="annotation">
                <xsl:apply-templates select="body/annotation" mode="section-content"/>
            </xsl:with-param>
        </xsl:call-template>
        <body>
            <section>
                <title>
                    <p><xsl:value-of select="$title"/></p>
                </title>
                <xsl:apply-templates select="body" mode="section-content"/>
            </section>
        </body>
        <body name="notes">
            <xsl:apply-templates select="body//footnote" mode="footnotes"/>
        </body>
        <xsl:call-template name="create-fb2-footer"/>
    </FictionBook>
</xsl:template>

<xsl:template match="body|footnote|annotation" mode="section-content">
    <xsl:apply-templates select="p" mode="paragraphs"/>
</xsl:template>

<xsl:template match="p" mode="paragraphs">
    <p><xsl:apply-templates select="node()" mode="body"/></p>
</xsl:template>

<xsl:template match="node()" mode="paragraphs">
    <xsl:apply-templates select="node()" mode="paragraphs"/>
</xsl:template>

<xsl:template match="i|em" mode="body">
    <emphasis><xsl:apply-templates select="node()" mode="body"/></emphasis>
</xsl:template>

<xsl:template match="b|strong" mode="body">
    <strong><xsl:apply-templates select="node()" mode="body"/></strong>
</xsl:template>

<xsl:template match="a" mode="body">
    <a xlink:href="{@href}">
        <xsl:apply-templates select="node()" mode="body"/>
        <xsl:if test="not(node())">
            <xsl:value-of select="concat('[', count(preceding::a[not(node())])+1, ']')"/>
        </xsl:if>
    </a>
</xsl:template>

<xsl:template match="img" mode="body">
    <a xlink:href="{@src}">
        <xsl:choose>
            <xsl:when test="@alt">
                <xsl:value-of select="@alt"/>
            </xsl:when>
            <xsl:when test="@title">
                <xsl:value-of select="@title"/>
            </xsl:when>
            <xsl:otherwise>
                <xsl:value-of select="re:replace(@src, '^.*/', '', '')"/>
            </xsl:otherwise>
        </xsl:choose>
    </a>
</xsl:template>

<xsl:template match="footnote" mode="body"/>

<xsl:template match="footnote" mode="footnotes">
    <section id="{@id}">
        <title><p><xsl:value-of select="count(preceding::footnote)+1"/></p></title>
        <xsl:apply-templates select="." mode="section-content"/>
    </section>
</xsl:template>
    
</xsl:stylesheet>